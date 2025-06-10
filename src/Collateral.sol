// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract Collateral is Initializable, OwnableUpgradeable, UUPSUpgradeable {
    uint16 public NETUID;
    uint64 public DECISION_TIMEOUT;
    uint256 public MIN_COLLATERAL_INCREASE;

    mapping(uint256 => Reclaim) public reclaims;
    mapping(address => uint256) public collaterals;
    mapping(address => uint256) private collateralUnderPendingReclaims;
    mapping(address => address) public validatorOfMiner;
    mapping(address => mapping(bytes16 => uint256)) public collateralPerExecutor;
    mapping(address => bytes16[]) private knownExecutorUuids;
    uint256 private nextReclaimId;

    struct Reclaim {
        address miner;
        uint256 amount;
        uint256 denyTimeout;
        bytes16 executorUuid;
    }

    event Deposit(address indexed account, uint256 amount);
    event ReclaimProcessStarted(
        uint256 indexed reclaimRequestId,
        address indexed account,
        uint256 amount,
        uint64 expirationTime,
        string url,
        bytes16 urlContentMd5Checksum
    );
    event Reclaimed(uint256 indexed reclaimRequestId, address indexed account, uint256 amount);
    event Denied(uint256 indexed reclaimRequestId, string url, bytes16 urlContentMd5Checksum);
    event Slashed(address indexed account, uint256 amount, string url, bytes16 urlContentMd5Checksum);
    event ValidatorUpdateAttemptFailed(address indexed miner, address indexed caller, address indexed newValidator);

    error AmountZero();
    error BeforeDenyTimeout();
    error InsufficientAmount();
    error InvalidDepositMethod();
    error NotTrustee();
    error PastDenyTimeout();
    error ReclaimAmountTooLarge();
    error ReclaimAmountTooSmall();
    error SlashAmountTooLarge();
    error ReclaimNotFound();
    error TransferFailed();

    /// @notice Initializes a new Collateral contract with specified parameters
    /// @param netuid The netuid of the subnet
    /// @param minCollateralIncrease The minimum amount that can be deposited or reclaimed
    /// @param decisionTimeout The time window (in seconds) for the validator to deny a reclaim request
    /// @dev Reverts if any of the arguments is zero
    function initialize(uint16 netuid, uint256 minCollateralIncrease, uint64 decisionTimeout) public initializer {
        require(minCollateralIncrease > 0, "Min collateral increase must be greater than 0");
        require(decisionTimeout > 0, "Decision timeout must be greater than 0");
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
        NETUID = netuid;
        MIN_COLLATERAL_INCREASE = minCollateralIncrease;
        DECISION_TIMEOUT = decisionTimeout;
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

    modifier onlyAssignedValidator(address miner) {
        if (validatorOfMiner[miner] != msg.sender) {
            revert NotTrustee();
        }
        _;
    }

    // Allow deposits only via deposit() function
    receive() external payable {
        revert InvalidDepositMethod();
    }

    // Allow deposits only via deposit() function
    fallback() external payable {
        revert InvalidDepositMethod();
    }

    /// @notice Allows users to deposit collateral into the contract
    /// @dev The deposited amount must be greater than or equal to MIN_COLLATERAL_INCREASE
    /// @dev If it's not revert with InsufficientAmount error
    /// @dev Emits a Deposit event with the sender's address and deposited amount
    function deposit(address validator, bytes16 executorUuid) external payable {
        if (msg.value < MIN_COLLATERAL_INCREASE) {
            revert InsufficientAmount();
        }

        require(validator != address(0), "Validator address must be non-zero");

        // Handle validator switch
        address currentValidator = validatorOfMiner[msg.sender];
        if (currentValidator != address(0) && currentValidator != validator) {
            // Only allow switch if miner has no pending reclaim
            require(collateralUnderPendingReclaims[msg.sender] == 0, "Cannot switch validator with pending reclaim");

            validatorOfMiner[msg.sender] = validator;

            // Optional: emit an event for validator switch
            // emit ValidatorChanged(msg.sender, currentValidator, validator);
        } else if (currentValidator == address(0)) {
            // First time deposit
            validatorOfMiner[msg.sender] = validator;
        }

        collaterals[msg.sender] += msg.value;

        if (collateralPerExecutor[msg.sender][executorUuid] == 0) {
            knownExecutorUuids[msg.sender].push(executorUuid);
        }
        
        collateralPerExecutor[msg.sender][executorUuid] += msg.value;

        emit Deposit(msg.sender, msg.value);
    }
    
    /// @notice Initiates a process to reclaim message sender's collateral from the contract
    /// @dev If it's not denied by the validator, the collateral will be available for withdrawal after DECISION_TIMEOUT
    /// @dev The amount reclaimed must be greater than 0
    /// @dev The amount reclaimed must be greater than or equal to MIN_COLLATERAL_INCREASE untless it's a full collateral withdrawal
    /// @dev The total amount under pending reclaims cannot exceed the user's total collateral
    /// @param amount The amount of collateral to reclaim
    /// @param url URL containing information about the reclaim request
    /// @param urlContentMd5Checksum MD5 checksum of the content at the provided URL
    /// @dev Emits ReclaimProcessStarted event with reclaim details and timeout
    /// @dev Reverts with ReclaimAmountTooSmall if amount is 0 or doesn't meet minimum requirements
    /// @dev Reverts with ReclaimAmountTooLarge if there's insufficient collateral available
    function reclaimCollateral(uint256 amount, string calldata url, bytes16 urlContentMd5Checksum, bytes16 executorUuid) external {
        if (amount == 0) {
            revert AmountZero();
        }

        if (collateralPerExecutor[msg.sender][executorUuid] < amount) {
            revert ReclaimAmountTooLarge(); // or define a new error for executor-specific limits
        }

        uint256 collateral = collaterals[msg.sender];
        uint256 pendingCollateral = collateralUnderPendingReclaims[msg.sender];
        uint256 collateralAvailableForReclaim = collateral - pendingCollateral;
        if (pendingCollateral + amount > collateral) {
            revert ReclaimAmountTooLarge();
        }
        if (amount < MIN_COLLATERAL_INCREASE && collateralAvailableForReclaim != amount) {
            revert ReclaimAmountTooSmall();
        }

        uint64 expirationTime = uint64(block.timestamp) + DECISION_TIMEOUT;
        reclaims[++nextReclaimId] = Reclaim(msg.sender, amount, expirationTime, executorUuid);
        collateralUnderPendingReclaims[msg.sender] += amount;

        emit ReclaimProcessStarted(nextReclaimId, msg.sender, amount, expirationTime, url, urlContentMd5Checksum);
    }

    /// @notice Finalizes a reclaim request and transfers the collateral to the depositor if conditions are met
    /// @dev Can be called by anyone
    /// @dev Requires that deny timeout has expired
    /// @dev If the miner has been slashed and their collateral is insufficient for a reclaim, the reclaim is canceled but transactions completes successfully allowing to request another reclaim
    /// @param reclaimRequestId The ID of the reclaim request to finalize
    /// @dev Emits Reclaimed event with reclaim details if successful
    /// @dev Reverts with ReclaimNotFound if the reclaim request doesn't exist or was denied
    /// @dev Reverts with BeforeDenyTimeout if the deny timeout hasn't expired
    /// @dev Reverts with TransferFailed if the TAO transfer fails
    function finalizeReclaim(uint256 reclaimRequestId) external {
        Reclaim memory reclaim = reclaims[reclaimRequestId];
        if (reclaim.amount == 0) {
            revert ReclaimNotFound();
        }
        if (reclaim.denyTimeout >= block.timestamp) {
            revert BeforeDenyTimeout();
        }
        if (validatorOfMiner[reclaim.miner] != msg.sender) {
            revert NotTrustee();
        }

        // Delete reclaim and update pending reclamation amount unconditionally
        delete reclaims[reclaimRequestId];
        collateralUnderPendingReclaims[reclaim.miner] -= reclaim.amount;
        // Only if the miner still has enough collateral do we process the withdrawal
        if (collaterals[reclaim.miner] >= reclaim.amount) {
            collateralPerExecutor[reclaim.miner][reclaim.executorUuid] -= reclaim.amount;
            collaterals[reclaim.miner] -= reclaim.amount;
            emit Reclaimed(reclaimRequestId, reclaim.miner, reclaim.amount);
            (bool success,) = payable(reclaim.miner).call{value: reclaim.amount}("");
            if (!success) {
                revert TransferFailed();
            }

            // If collateral for this executor is now zero, remove it from knownExecutorUuids
            if (collateralPerExecutor[reclaim.miner][reclaim.executorUuid] == 0) {
                bytes16[] storage minerExecutors = knownExecutorUuids[reclaim.miner];
                for (uint i = 0; i < minerExecutors.length; i++) {
                    if (minerExecutors[i] == reclaim.executorUuid) {
                        // Swap with the last element and shrink the array
                        minerExecutors[i] = minerExecutors[minerExecutors.length - 1];
                        minerExecutors.pop();
                        break; // Found and removed, exit loop
                    }
                }
            }
        }
        // Otherwise miner got slashed: reclaim request is deleted without transferring funds
    }

    /// @notice Allows the validator to deny a pending reclaim request before the timeout expires
    /// @dev Can only be called by the assigned validator
    /// @dev Must be called before the deny timeout expires
    /// @param reclaimRequestId The ID of the reclaim request to deny
    /// @param url URL containing the reason of denial
    /// @param urlContentMd5Checksum MD5 checksum of the content at the provided URL
    /// @dev Emits Denied event with the reclaim request ID
    /// @dev Reverts with ReclaimNotFound if the reclaim request doesn't exist
    /// @dev Reverts with PastDenyTimeout if the timeout has already expired
    function denyReclaimRequest(uint256 reclaimRequestId, string calldata url, bytes16 urlContentMd5Checksum)
        external
    {
        Reclaim memory reclaim = reclaims[reclaimRequestId];
        if (reclaim.amount == 0) {
            revert ReclaimNotFound();
        }

        if (validatorOfMiner[reclaim.miner] != msg.sender) {
            revert NotTrustee();
        }

        if (reclaim.denyTimeout < block.timestamp) {
            revert PastDenyTimeout();
        }
      
        collateralUnderPendingReclaims[reclaim.miner] -= reclaim.amount;
        emit Denied(reclaimRequestId, url, urlContentMd5Checksum);

        delete reclaims[reclaimRequestId];
    }

    /// @notice Allows the validator to slash a miner's collateral
    /// @dev Can only be called by the assigned validator
    /// @param miner The address of the miner to slash
    /// @param amount The amount of collateral to slash, must be greater than 0
    /// @param url URL containing the reason for slashing
    /// @param urlContentMd5Checksum MD5 checksum of the content at the provided URL
    /// @param executorUuid The UUID of the executor associated with the slashed collateral
    /// @dev Emits Slashed event with the miner's address and the amount slashed
    /// @dev Reverts with AmountZero if amount is 0
    /// @dev Reverts with InsufficientAmount if the miner has less collateral than the amount to slash
    /// @dev Reverts with TransferFailed if the TAO transfer fails
    function slashCollateral(address miner, uint256 amount, string calldata url, bytes16 urlContentMd5Checksum, bytes16 executorUuid)
        external
    {
        if (amount == 0) {
            revert AmountZero();
        }
        if (collaterals[miner] < amount) {
            revert InsufficientAmount();
        }

        if (collateralPerExecutor[miner][executorUuid] < amount) {
            revert SlashAmountTooLarge(); // or define a new error for executor-specific limits
        }

        // Ensure only assigned validator can slash
        if (validatorOfMiner[miner] != msg.sender) {
            revert NotTrustee();
        }
        
        collaterals[miner] -= amount;
        // burn the collateral
        (bool success,) = payable(address(0)).call{value: amount}("");
        if (!success) {
            revert TransferFailed();
        }

        collateralPerExecutor[miner][executorUuid] -= amount;

        emit Slashed(miner, amount, url, urlContentMd5Checksum);
    }

   /// @notice Returns a list of executors for a specific miner that have more than 0 TAO in collateral
    /// @dev This function checks the `collateralPerExecutor` mapping for the specified miner's executors.
    /// @param miner The address of the miner for whom the executors are to be fetched.
    /// @return A dynamic array of `bytes16` UUIDs representing executors with more than 0 TAO in collateral for the specified miner.
    /// @notice Returns a list of eligible executors for a specific miner that have more than 0 TAO in collateral and have not been slashed or penalized.
    function getEligibleExecutors(address miner) external view returns (bytes16[] memory) {
        bytes16[] memory allExecutors = knownExecutorUuids[miner];
        uint256 count = 0;

        // First pass to count
        for (uint256 i = 0; i < allExecutors.length; i++) {
            if (collateralPerExecutor[miner][allExecutors[i]] > 0) {
                count++;
            }
        }

        // Second pass to collect
        bytes16[] memory eligible = new bytes16[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < allExecutors.length; i++) {
            if (collateralPerExecutor[miner][allExecutors[i]] > 0) {
                eligible[index++] = allExecutors[i];
            }
        }

        return eligible;
    }

    /// @notice Updates the validator for a specific miner and transfers associated collateral
    /// @dev Can only be called by the current validator of the miner
    /// @param miner The address of the miner whose validator is being updated
    /// @param newValidator The address of the new validator
    function updateValidatorForMiner(address miner, address newValidator) external {
        if (miner != msg.sender) {
            emit ValidatorUpdateAttemptFailed(miner, msg.sender, newValidator);
            revert NotTrustee();
        }
        if (newValidator == address(0)) {
            revert InvalidDepositMethod();
        }

        validatorOfMiner[miner] = newValidator;
    }

    /// @notice Returns the next available reclaim request ID.
    /// @return The next reclaim request ID.
    function getNextReclaimId() external view returns (uint256) {
        return nextReclaimId;
    }

    /// @notice Returns a list of active reclaim requests (amount > 0).
    /// @return A dynamic array of Reclaim structs.
    function getReclaims() external view returns (Reclaim[] memory) {
        uint256 totalReclaims = nextReclaimId;
        uint256 eligibleCount = 0;

        // First pass to count the number of eligible reclaims
        for (uint256 i = 1; i <= totalReclaims; i++) {
            if (reclaims[i].amount > 0) {
                eligibleCount++;
            }
        }

        // Create an array of the exact size needed
        Reclaim[] memory eligibleReclaims = new Reclaim[](eligibleCount);
        uint256 currentIndex = 0;

        // Second pass to populate the array with eligible reclaims
        for (uint256 i = 1; i <= totalReclaims; i++) {
            Reclaim storage currentReclaim = reclaims[i];
            if (currentReclaim.amount > 0) {
                eligibleReclaims[currentIndex] = currentReclaim;
                currentIndex++;
            }
        }

        return eligibleReclaims;
    }
}