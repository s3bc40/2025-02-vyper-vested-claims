## Informational

### [I-1] No pragma directives does not ensure version compatibility

**Description:** 

Pragma directive is missing in `VestedAirdrop.vy`,letting the contract to be compiled by any compiler version. To ensure version compatibility, it is recommended to add a pragma directive with a specific version.

**Recommended Mitigation:** 
```py
# pragma version 0.4.0
```


### [I-2] Avoid using magic numbers to enhance clarity and readability

**Description:** 

Magic numbers are used in the code to store constants, making the code less readable. It is recommended to use constants instead.

Here are the magic numbers used in the code:
```py
proof: DynArray[bytes32, 20] # why 20 is selected? max length?
# 31 and 69 are explained in the contract description
# but it could be more explicit as for 100 as the precision
instant_release:  uint256 = (total_amount * 31) // 100
linear_vesting:   uint256 = (total_amount * 69) // 100
```

**Recommended Mitigation:** 

Create proper constants with clear names can enhance readability:
```py
PRECISION: uint256 = 100
TGE_RELEASE_PERCENT: uint256 = 31 # Token Generation Event
LINEAR_VESTING_PERCENT: uint256 = 69
MAX_PROOF_LENGTH: uint256 = 20
```

## Gas

### [G-1] Store variables should be immutable to improve gas efficiency

**Description:** 
The following store variables are initialized in the constructor but not changed after that: 

```py
vesting_start_time: public(uint256)
vesting_end_time:   public(uint256)
token:              public(address)
owner:              public(address)
```

Immutables are not stored in the storage but as a part of the contract. So changing them to immutable could improve the gas efficiency.

**Recommended Mitigation:** 
```diff
- vesting_start_time: public(uint256)
- vesting_end_time:   public(uint256)
- token:              public(address)
- owner:              public(address)
+ VESTING_START_TIME: public(immutable(uint256))
+ VESTING_END_TIME:   public(immutable(uint256))
+ TOKEN:              public(immutable(address))
+ OWNER:              public(immutable(address))
```

## Low
### [L-1] Lacking of ownership transferability can lead to scalability issues

**Description:** 
Owner is trusted so this issue could be low or just informational. But `VestedAirdrop::rescue_tokens` and `VestedAirdrop::set_merkle_root` are dependent on the owner. Ownership is only set once during deployment of the contract and cannot be changed afterwards. As the protocol will evolve, this might be a problem in the future if different roles are assigned to different addresses, or the current owner changes for the protocol. If the owner is changed after deployment in the protocol, then this contract will not work as expected and we would need to deploy a new contract with the new owner.

**Recommended Mitigation:** 

Add the trusted `snekmate` dependency and use the `ownable` library to allow features like ownership transferability or checking the owner.

```bash
mox install snekmate
```

Import the `ownable` snekmate library:
```py
from snekmate.auth import ownable

initializes: ownable
```

It should add the following functions to the contract:
```py
@internal
# replacing the custom def onlyOwner():
def _check_owner():
    ...

def _transfer_ownership(new_owner: address):
    ...
```

Then export this specific external function:
```py
exports: (
    ownable.transfer_ownership
    # other if needed
)  
```

And invoke __init__ inside the constructor:
```py
def __init__():
    ownable.__init__()
```

### [L-2] Failure on time-bound tests might come from deployment time and warp time method

**Description:** 
A known issue has been reported in the `VestedAirdrop` contract: *Time-bound tests fails for an issue in Titanoboa. The issue is being tracked [here](https://github.com/vyperlang/titanoboa/issues/380) and [here](https://github.com/Cyfrin/moccasin/issues/193)*. But it seems that the tests are rightfully failing because of the random second difference between EVM block timestamps and `datetime` timestamps in seconds. Also the method used to warp time might not be adapted to the test environment. The combination of these two issues might explain the failure of time-bound tests. But normally these issues are not expected to occur in production.

**Impact:** 
Time-bound tests fails on these tests:
- `TestVestingSystem::test_claim`
- `TestVestingSystem::test_claim_all`

Wrong claim amount are returned and the assert fails. 

**Proof of Concept:**
1. Printing the timestamp while deploying the contract to check the second difference:
```py
current_time = int(boa.env.evm.patch.timestamp)
print("EVM time:", current_time)
current_time = int(datetime.now().timestamp())
print("Datetime time:", current_time)

"""
WORKING:
EVM time: 1740258736
Datetime time: 1740258736
.EVM time: 1740258736
Datetime time: 1740258736
.EVM time: 1740258736

NOT WORKING:
Datetime time: 1740258791
FEVM time: 1740258792
Datetime time: 1740258791
FEVM time: 1740258792
"""
```

2. Checking the claimable amount against the expected amount (example with 30 days):
```py
# def test_claimable_amount(self):
# after 30 days
warp(time_now + thirty_days())
claimable = self.airdrop.claimable_amount(self.user1, self.amount)
print("claimable:", claimable)
print(
    "expected:",
    (self.amount * 31 // 100)
    + (linear_vesting * thirty_days()) // ninety_days(),
)
assert (
    claimable
    == (self.amount * 31 // 100)
    + (linear_vesting * thirty_days()) // ninety_days()
)

"""
claimable: 54000008873456790123
expected: 54000000000000000000

OR 

claimable: 22999991126543209877
expected: 23000000000000000000
"""
```

**Recommended Mitigation:** 
1. Deploy the contract with boa env timestamp rather than datetime.
```py
def deploy() -> VyperContract:
    current_time = int(boa.env.evm.patch.timestamp)
```

2. Use `boa.env.time_travel` instead of custom warping to take into account the block number too.
```py
boa.env.time_travel(THIRTY_DAYS)
```

I propose a reworked test file with all the original tests but with the recommended mitigation on my fork:
https://github.com/s3bc40/2025-02-vyper-vested-claims/blob/92c54dd15738435b4db2245655fbef0c8a0fa0b6/tests/test_audit.py

## Medium

## High


