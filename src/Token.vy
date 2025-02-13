from ethereum.ercs import IERC20
implements: IERC20

# ERC20
name:        public(String[32])
symbol:      public(String[32])
decimals:    public(uint8)
totalSupply: public(uint256)
balanceOf:   public(HashMap[address, uint256])
allowance:   public(HashMap[address, HashMap[address, uint256]])

@deploy
def __init__():
    _supply: uint256 = 1_000_000 * 10**18
    self.name                  = "Token"
    self.symbol                = "TKN"
    self.decimals              = 18
    self.totalSupply           = _supply
    self.balanceOf[msg.sender] = _supply
    log IERC20.Transfer(empty(address), msg.sender, _supply)

# ERC20 Functions

def _update(_from: address, _to: address, _value: uint256):
    self.balanceOf[_from] -= _value
    self.balanceOf[_to]   += _value
    log IERC20.Transfer(_from, _to, _value)

def _transfer(_from: address, _to: address, _value: uint256):
    self._update(_from, _to, _value)

@external
def transfer(_to: address, _value: uint256) -> bool:
    self._transfer(msg.sender, _to, _value)
    return True

@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.allowance[_from][msg.sender] -= _value
    self._transfer(_from, _to, _value)
    return True

@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    log IERC20.Approval(msg.sender, _spender, _value)
    return True

@external
def burn(_value: uint256):
    self._update(msg.sender, empty(address), _value)
    self.totalSupply -= _value