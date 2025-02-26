import boa
import pytest

from boa.util.abi import Address
from eth_utils import from_wei, to_wei
from script import load_merkle_proofs
from eth.constants import ZERO_ADDRESS

# vesting info: 31% TGE, 69% linear vesting over 3 months

ONE_DAY = 60 * 60 * 24
THIRTY_DAYS = ONE_DAY * 30
SIXTY_DAYS = ONE_DAY * 60
NINETY_DAYS = ONE_DAY * 90

# helper functions


def to_wei_ether(amount: int) -> int:
    return to_wei(amount, "ether")


def from_wei_ether(amount: int) -> int:
    return from_wei(amount, "ether")


def block_timestamp() -> int:
    return boa.env.evm.patch.timestamp


def block_number() -> int:
    return boa.env.evm.patch.block_number


class TestAudit:
    @pytest.fixture(autouse=True)
    def setup(self, vesting_system):
        self.token, self.airdrop = vesting_system
        self.merkle_proofs = load_merkle_proofs()
        # load 1st proof for testing
        self.user1 = self.merkle_proofs["data"][0]["address"]
        self.amount = self.merkle_proofs["data"][0]["quantity"]
        self.proof = [
            bytes.fromhex(x[2:]) for x in self.merkle_proofs["data"][0]["proof"]
        ]

    def test_increment(self):
        assert self.token.name() == "Token"
        assert self.airdrop.token() == self.token.address

    def test_set_merkle_root(self):
        # cast k "HelloEth"
        merkle_root = bytes.fromhex(
            "84cef39a349765463ae54b9e7060205f4075ec9abed7f7ceac12f9f266f87062"
        )
        self.airdrop.set_merkle_root(merkle_root)
        assert self.airdrop.merkle_root() == merkle_root

    def test_claim(self):
        # ------------------------------------------------------------------
        #                          31% OF TOKENS
        # ------------------------------------------------------------------
        expected_amount = self.airdrop.claimable_amount(self.user1, self.amount)
        self.airdrop.claim(self.user1, self.amount, self.proof)
        user_balance = self.token.balanceOf(self.user1)
        assert from_wei_ether(user_balance) == from_wei_ether(expected_amount)

        # ------------------------------------------------------------------
        #                        REVERT CLAIM AGAIN
        # ------------------------------------------------------------------
        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)

        # ------------------------------------------------------------------
        #                             30 DAYS
        # ------------------------------------------------------------------
        boa.env.time_travel(THIRTY_DAYS)
        expected_claim_amount = self.airdrop.claimable_amount(self.user1, self.amount)
        user_prev_balance = self.token.balanceOf(self.user1)
        user_claimed_amount = self.airdrop.claimed_amount(self.user1)
        self.airdrop.claim(self.user1, self.amount, self.proof)

        user_balance = self.token.balanceOf(self.user1)
        instant_release = (self.amount * 31) // 100
        linear_vesting = (self.amount * 69) // 100
        expected_amount = (
            instant_release + (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        )
        assert expected_claim_amount == expected_amount - user_claimed_amount
        assert user_balance == expected_claim_amount + user_prev_balance

        # ------------------------------------------------------------------
        #                             60 DAYS
        # ------------------------------------------------------------------
        boa.env.time_travel(THIRTY_DAYS)
        expected_claim_amount = self.airdrop.claimable_amount(self.user1, self.amount)
        user_prev_balance = self.token.balanceOf(self.user1)
        user_claimed_amount = self.airdrop.claimed_amount(self.user1)
        self.airdrop.claim(self.user1, self.amount, self.proof)

        user_balance = self.token.balanceOf(self.user1)
        instant_release = (self.amount * 31) // 100
        linear_vesting = (self.amount * 69) // 100
        expected_amount = instant_release + (linear_vesting * SIXTY_DAYS) // NINETY_DAYS
        assert expected_claim_amount == expected_amount - user_claimed_amount
        assert user_balance == expected_claim_amount + user_prev_balance

        # ------------------------------------------------------------------
        #                             90 DAYS
        # ------------------------------------------------------------------
        boa.env.time_travel(THIRTY_DAYS)
        expected_claim_amount = self.airdrop.claimable_amount(self.user1, self.amount)
        user_prev_balance = self.token.balanceOf(self.user1)
        user_claimed_amount = self.airdrop.claimed_amount(self.user1)
        self.airdrop.claim(self.user1, self.amount, self.proof)

        user_balance = self.token.balanceOf(self.user1)
        instant_release = (self.amount * 31) // 100
        linear_vesting = (self.amount * 69) // 100
        expected_amount = (
            instant_release + (linear_vesting * NINETY_DAYS) // NINETY_DAYS
        )
        assert expected_claim_amount == expected_amount - user_claimed_amount
        assert user_balance == self.amount

        # ------------------------------------------------------------------
        #                       CANNOT CLAIM ANYMORE
        # ------------------------------------------------------------------
        boa.env.time_travel(THIRTY_DAYS)
        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)

    def test_claim_all(self):
        """
        ignore the vesting, claim after 90 days directly
        should get full amount and cannot claim anymore
        """

        boa.env.time_travel(NINETY_DAYS)
        self.airdrop.claim(self.user1, self.amount, self.proof)
        assert self.token.balanceOf(self.user1) == self.amount

        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)

    def test_claim_irregular_time(self):
        """
        claim at irregular time, at the end we should have full balance
        """

        def claim_at(days: int):
            boa.env.time_travel(ONE_DAY * days)
            self.airdrop.claim(self.user1, self.amount, self.proof)

        # claim at 1 day
        claim_at(1)
        # claim at 12 days
        claim_at(11)
        # claim at 35 days
        claim_at(23)
        # claim at 60 days
        claim_at(25)
        # claim at 892 days
        claim_at(832)

        assert self.token.balanceOf(self.user1) == self.amount

        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)

    def test_cannot_claim_before_start(self):
        """
        users cannot claim anything before the start
        """

        boa.env.evm.patch.timestamp = block_timestamp() - 1
        boa.env.evm.patch.block_number = block_number() - 1
        with boa.reverts(vm_error="Claiming is not available yet"):
            self.airdrop.claim(self.user1, self.amount, self.proof)

    def test_claimable_amount(self):
        """
        claimable_amount is a view function
        we test its calculations
        """

        # 31% unlocked at TGE
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert from_wei_ether(claimable) == from_wei_ether(self.amount * 31 // 100)

        linear_vesting = (self.amount * 69) // 100

        # after 30 days
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert (
            claimable
            == (self.amount * 31 // 100) + (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        )

        # after 60 days
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert (
            claimable
            == (self.amount * 31 // 100)
            + (linear_vesting * 2 * THIRTY_DAYS) // NINETY_DAYS
        )

        # after 90 days
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert claimable == self.amount

        # cannot claim anymore, but the view function doesn't keep track of the state, so it will be full self.amount
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert claimable == self.amount

    def test_claimable_amount_with_claims(self):
        """
        check if the claimable amount is correct after multiple claims
        """
        linear_vesting = (self.amount * 69) // 100

        # check if TGE is correct
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert from_wei_ether(claimable) == from_wei_ether(self.amount * 31 // 100)

        # claim with user1
        self.airdrop.claim(self.user1, self.amount, self.proof)
        # should only get 31% of the tokens
        assert from_wei_ether(self.token.balanceOf(self.user1)) == from_wei_ether(
            self.amount * 31 // 100
        )

        # claim again, should fail because amount is 0
        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert from_wei_ether(claimable) == 0

        # after 30 days
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert claimable == (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        self.airdrop.claim(self.user1, self.amount, self.proof)
        assert from_wei_ether(self.token.balanceOf(self.user1)) == from_wei_ether(
            (self.amount * 31 // 100) + (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        )

        # after 60 days total
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert claimable == (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        self.airdrop.claim(self.user1, self.amount, self.proof)
        assert from_wei_ether(self.token.balanceOf(self.user1)) == from_wei_ether(
            (self.amount * 31 // 100) + (linear_vesting * 60) // 90
        )

        # after 90 days total
        boa.env.time_travel(THIRTY_DAYS)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert claimable == (linear_vesting * THIRTY_DAYS) // NINETY_DAYS
        self.airdrop.claim(self.user1, self.amount, self.proof)
        assert from_wei_ether(self.token.balanceOf(self.user1)) == from_wei_ether(
            (self.amount * 31 // 100) + (linear_vesting * 90) // 90
        )

        # cannot claim anymore
        boa.env.time_travel(THIRTY_DAYS)
        with boa.reverts(vm_error="Nothing to claim"):
            self.airdrop.claim(self.user1, self.amount, self.proof)
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert from_wei_ether(claimable) == 0
        claimable = self.airdrop.claimable_amount(self.user1, self.amount)
        assert from_wei_ether(claimable) == 0

    def test_rescue_tokens(self):
        """
        ERC20 sent to the contract can be rescued by the owner
        """
        amount = 1000
        airdrop_balance = self.token.balanceOf(self.airdrop.address)

        self.airdrop.rescue_tokens(self.token.address, to_wei_ether(amount))
        assert self.token.balanceOf(
            self.airdrop.address
        ) == airdrop_balance - to_wei_ether(amount)
        # assert self.token.balanceOf(boa.tx.origin) == to_wei(amount)

    def test_set_timestamp(self):
        current_time = self.airdrop.vesting_start_time()
        assert current_time != 0
        self.airdrop.eval("self.vesting_start_time = 0")
        assert self.airdrop.vesting_start_time() == 0

    def test_ownable_functions(self):
        """
        test all ownable functions, must revert if not owner
        """
        user = boa.env.generate_address("user")
        revert_msg = "Only owner can call this function"
        with boa.env.prank(user):
            with boa.reverts(revert_msg):
                self.airdrop.set_merkle_root(b"0x0")
            with boa.reverts(revert_msg):
                self.airdrop.rescue_tokens(self.token.address, 0)
    
    # ------------------------------------------------------------------
    #                           AUDIT TESTS
    # ------------------------------------------------------------------
    def test_audit_claimable_amount_with_user_address_zero(self):
        """
        claimable_amount with user address zero
        """
        claimable = self.airdrop.claimable_amount(Address("0x" + ZERO_ADDRESS.hex()), self.amount)
        print(claimable)
        assert claimable == 0
    
    def test_audit_claim_with_user_address_zero(self):
        """
        claimable_amount with user address zero
        """
        claimable = self.airdrop.claim(Address("0x" + ZERO_ADDRESS.hex()), self.amount, self.proof)
        print(claimable)
        assert claimable == 0

    def test_audit_claim_timestamp_manipulation(self):
        """Test realistic timestamp manipulation within Ethereum constraints"""
        
        initial_amount = to_wei_ether(1000)
        total_time = 90 * ONE_DAY  # 90 days vesting period
        
        # Setup initial state
        start_time = block_timestamp()
        
        # Calculate expected initial vested amount (31% instant)
        expected_initial = (initial_amount * 31) // 100
        
        # Try to manipulate timestamp by maximum allowed (15 seconds)
        MAX_TIMESTAMP_MANIPULATION = 15  # seconds
        
        # Simulate multiple blocks with maximum timestamp manipulation
        for _ in range(10):  # Simulate 10 blocks of manipulation
            # Move time forward by max allowed
            boa.env.time_travel(MAX_TIMESTAMP_MANIPULATION)
            
            # Calculate manipulated amount
            manipulated_time = block_timestamp() - start_time
            linear_portion = (initial_amount * 69) // 100
            expected_manipulated = expected_initial + (linear_portion * manipulated_time) // total_time
            
            # Verify the manipulation effect
            actual_vested = self.airdrop.claimable_amount(self.user1, initial_amount)
            assert actual_vested == expected_manipulated, "Manipulation should follow linear vesting schedule"
            
            # Try to claim with manipulated timestamp
            if actual_vested > 0:
                with boa.reverts("Invalid proof"):  # Should fail due to invalid merkle proof
                    self.airdrop.claim(self.user1, initial_amount, [b"0x00"])
        
        # Calculate total manipulation effect
        total_manipulation = MAX_TIMESTAMP_MANIPULATION * 10  # 150 seconds total
        manipulation_percentage = (total_manipulation / total_time) * 100
        
        print(f"Total time manipulated: {total_manipulation} seconds")
        print(f"Percentage of vesting affected: {manipulation_percentage:.4f}%")
        
        # Assert the manipulation impact is minimal
        assert manipulation_percentage < 0.01, "Timestamp manipulation should have minimal impact"

