// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "hardhat/console.sol"; // Import console for logging

contract ValueStore {
    struct Entry {
        uint256 number;
        string text;
        bool flag;
    }

    Entry[] public entries;
    bytes16[] public knownExecutorUuids;
    uint256[] public numbers;

    event TransactionFailed(address sender, string reason);

    function addEntry(uint256 _number, string memory _text, bool _flag) public {
        console.log("addEntry called with:", _number, _text, _flag); // Log the parameters
        if (_number == 0) {
            emit TransactionFailed(msg.sender, "Number cannot be zero");
            revert("Number cannot be zero");
        }
        entries.push(Entry(_number, _text, _flag));
        numbers.push(_number);
        knownExecutorUuids.push(bytes16(abi.encodePacked("162a6ca8-cd29-40c8-be25-1cb1ac76e3ad")));

        console.log("addEntry call finished with:", _number, _text, _flag); // Log the parameters
    }

    function getEntry(uint index) public view returns (uint256, string memory, bool) {
        require(index < entries.length, "Index out of bounds: Invalid index");
        Entry memory e = entries[index];
        return (e.number, e.text, e.flag);
    }

    function getExecutors() external view returns (bytes16[] memory) {
        return knownExecutorUuids;
    }

    function getNumbers() external view returns (uint256[] memory) {
        return numbers;
    }

    function getCount() public view returns (uint256) {
        return entries.length;
    }
}
