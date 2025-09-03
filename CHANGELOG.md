# Changelog

## [1.1.6] - 2025-09-03
### Added
- Support for burn address in contract deployment and operations
- New `BURN_ADDRESS()` function to retrieve the configured burn address
- Partial slashing functionality with configurable slash amounts
- Enhanced slashing function with amount parameter

### Changed
- Updated contract constructor to accept burn address parameter
- Modified slash operation to include slash amount in TAO
- Refactored checksum calculation to be asynchronous using aiohttp
- Updated deploy scripts to include burn address argument
- Enhanced ABI with new burn address and slash amount parameters
- Improved error handling and logging output to stderr

### Updated

## [1.1.5] - 2025-08-22
### Fixed
- Remove bittensor packages usages.