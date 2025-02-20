# Protocol Name 


### Prize Pool

- Starts: February 20, 2025 
- Ends: February 27, 2025

[//]: # (contest-details-open)

## About the Project


This smart contract is designed for distributing tokens with a vesting schedule.
The contract uses Merkle trees for claims, allowing 31% of tokens to be released at the Token Generation Event (TGE) and the remaining 69% to be released linearly over time.

## Actors

- **Contract Owner (Trusted)**: 
  - Can set the Merkle root
  - Can rescue tokens in emergency situations

- **Users**: 
  - Can claim vested tokens
  - Must provide a valid Merkle proof to claim tokens

[//]: # (contest-details-close)

[//]: # (scope-open)

## Scope (contracts)

```
├── src
│   ├── VestedAirdrop.vy
```

## Compatibilities

  Blockchains:
    - Any EVM-compatible blockchain
  Tokens:
    - ERC20 tokens with 18 decimals.
    - Standard ERC20s only
    - FoT and Rebasing tokens are unsupported.

[//]: # (scope-close)

[//]: # (getting-started-open)

## Setup

Requires [Moccasin](https://github.com/Cyfrin/moccasin) to be installed.

```bash
mox test
```

[//]: # (getting-started-close)

[//]: # (known-issues-open)

## Known Issues

Time-bound tests fails for an issue in Titanoboa. The issue is being tracked [here](https://github.com/vyperlang/titanoboa/issues/380) and [here](https://github.com/Cyfrin/moccasin/issues/193)

[//]: # (known-issues-close)
