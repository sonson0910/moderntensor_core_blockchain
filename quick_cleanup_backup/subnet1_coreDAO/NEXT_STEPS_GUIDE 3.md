# 🚀 ModernTensor Network - Next Steps Guide

## ✅ Current Status
**ALL 5 ENTITIES FROM @entities/ SUCCESSFULLY REGISTERED!**
- 2 Miners registered on Subnet 1
- 3 Validators registered on Subnet 1
- Network ready for operation

## 📋 Next Steps to Start Network

### 1. 🖥️ Start Network Manager
```bash
cd subnet1_aptos
python start_network.py
```

### 2. 🛡️ Start Individual Validators
Open separate terminals for each validator:

**Terminal 1 - Validator 1:**
```bash
cd subnet1_aptos
python -m subnet1.validator --config entities/validator_1.json --port 8001
```

**Terminal 2 - Validator 2:**
```bash
cd subnet1_aptos  
python -m subnet1.validator --config entities/validator_2.json --port 8002
```

**Terminal 3 - Validator 3:**
```bash
cd subnet1_aptos
python -m subnet1.validator --config entities/validator_3.json --port 8003
```

### 3. 🔨 Start Miners
Open separate terminals for each miner:

**Terminal 4 - Miner 1:**
```bash
cd subnet1_aptos
python -m subnet1.miner --config entities/miner_1.json --port 8101
```

**Terminal 5 - Miner 2:**
```bash
cd subnet1_aptos
python -m subnet1.miner --config entities/miner_2.json --port 8102
```

### 4. 📊 Monitor Network
```bash
# Check network status
export CORE_CONTRACT_ADDRESS='0x594fc12B3e3AB824537b947765dd9409DAAAa143'
python final_network_check.py

# Monitor consensus
python monitor_consensus.py

# Check CLI
python -m moderntensor_aptos.mt_core.cli.metagraph_cli list-miners
python -m moderntensor_aptos.mt_core.cli.metagraph_cli list-validators
```

## 🔧 Configuration Details

### Contract Address
```
0x594fc12B3e3AB824537b947765dd9409DAAAa143
```

### Subnet Details
- **Subnet ID:** 1
- **Min Stake:** 0.01 CORE
- **Registration:** OPEN ✅

### Entity Configurations
All entities in `entities/` directory are configured with:
- ✅ Private keys and addresses
- ✅ Sufficient CORE tokens
- ✅ API endpoints (localhost:800X)
- ✅ Registered on blockchain

## 🌐 Network Endpoints
- **Validators:** http://localhost:8001-8003
- **Miners:** http://localhost:8101-8102
- **RPC:** https://rpc.test.btcs.network
- **Explorer:** https://scan.test.btcs.network

## 🎯 Expected Behavior
Once started:
1. Validators will begin consensus rounds
2. Miners will receive and process AI tasks  
3. Performance scoring and rewards distribution
4. Trust score updates
5. ModernTensor consensus active

## 🚨 Troubleshooting
If issues occur:
1. Check entity balances: `python debug_registration.py`
2. Verify network connectivity: `python final_network_check.py`
3. Restart individual components
4. Check logs for specific errors

## 📈 Success Metrics
- ✅ 2+ Miners active
- ✅ 3+ Validators active  
- ✅ Consensus rounds completing
- ✅ Tasks being distributed and scored
- ✅ Rewards being distributed

**🎉 MODERNTENSOR NETWORK IS READY FOR LAUNCH! 🎉**