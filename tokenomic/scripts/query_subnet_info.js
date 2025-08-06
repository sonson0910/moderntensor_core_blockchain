// scripts/query_network_info.js
const { ethers } = require("hardhat");

async function main() {
    try {
        // Load ABI
        const ModernTensorABI = JSON.parse(require('fs').readFileSync("./abis/ModernTensor.json", "utf8")).abi;

        // Config
        const RPC_URL = process.env.RPC_URL || "https://rpc.test2.btcs.network";
        const CONTRACT_ADDRESS = process.env.SOL_ADDRESS || "0xAA6B8200495F7741B0B151B486aEB895fEE8c272";
        const provider = new ethers.JsonRpcProvider(RPC_URL);
        const [signer] = await ethers.getSigners();
        console.log("Tài khoản thực hiện:", signer.address);

        // Kết nối hợp đồng
        const modernTensor = new ethers.Contract(CONTRACT_ADDRESS, ModernTensorABI, provider);
        const modernTensorWithSigner = new ethers.Contract(CONTRACT_ADDRESS, ModernTensorABI, signer);

        // Kiểm tra mạng
        const network = await provider.getNetwork();
        console.log("Kết nối đến mạng:", network.name, "Chain ID:", network.chainId);

        // Kiểm tra hợp đồng
        const code = await provider.getCode(CONTRACT_ADDRESS);
        if (code === "0x") {
            throw new Error(`Không tìm thấy hợp đồng tại địa chỉ ${CONTRACT_ADDRESS}`);
        }
        console.log("Tìm thấy hợp đồng tại địa chỉ:", CONTRACT_ADDRESS);

        // Kiểm tra trạng thái hợp đồng
        console.log("Kiểm tra trạng thái hợp đồng...");
        try {
            const coreToken = await modernTensor.coreToken();
            console.log("Địa chỉ CoreToken:", coreToken);
            const nextSubnetId = await modernTensor.nextSubnetId();
            console.log("Số lượng subnet đã đăng ký (nextSubnetId):", nextSubnetId.toString());
        } catch (error) {
            console.warn("Lỗi khi kiểm tra trạng thái hợp đồng:", error.message);
            if (error.info) console.warn("Thông tin lỗi:", error.info);
        }

        // Lấy danh sách tất cả subnet
        console.log("Lấy danh sách subnet...");
        let subnetIds = [];
        try {
            subnetIds = await modernTensor.getAllSubnetIds();
            console.log("📍 Danh sách subnet IDs:", subnetIds.map(id => id.toString()));
        } catch (error) {
            console.error("❌ Lỗi khi lấy danh sách subnet:", error.message);
            if (error.info) console.error("Thông tin:", error.info);
        }

        // Lấy thông tin chi tiết tất cả subnet
        const allSubnetInfo = [];
        for (const id of subnetIds) {
            try {
                const [staticData, dynamicData, minerAddresses, validatorAddresses] = await modernTensor.getSubnet(id);
                const formattedSubnet = {
                    subnetId: staticData.net_uid.toString(),
                    staticData: {
                        name: staticData.name,
                        owner: staticData.owner_addr,
                        maxMiners: staticData.max_miners.toString(),
                        maxValidators: staticData.max_validators.toString(),
                        immunityPeriod: staticData.immunity_period.toString(),
                        creationTime: new Date(Number(staticData.creation_time) * 1000).toISOString(),
                        description: staticData.description,
                        version: staticData.version.toString(),
                        minStakeMiner: ethers.formatUnits(staticData.min_stake_miner, 18),
                        minStakeValidator: ethers.formatUnits(staticData.min_stake_validator, 18)
                    },
                    dynamicData: {
                        currentEpoch: dynamicData.current_epoch.toString(),
                        scaledWeight: (Number(dynamicData.scaled_weight) / 1_000_000).toFixed(6),
                        scaledPerformance: (Number(dynamicData.scaled_performance) / 1_000_000).toFixed(6),
                        registrationOpen: dynamicData.registration_open === 1,
                        regCost: ethers.formatUnits(dynamicData.reg_cost, 18),
                        scaledIncentiveRatio: (Number(dynamicData.scaled_incentive_ratio) / 1_000_000).toFixed(6),
                        lastUpdateTime: new Date(Number(dynamicData.last_update_time) * 1000).toISOString(),
                        totalStake: ethers.formatUnits(dynamicData.total_stake, 18),
                        totalBitcoinStake: dynamicData.total_bitcoin_stake.toString(),
                        validatorCount: dynamicData.validator_count.toString(),
                        minerCount: dynamicData.miner_count.toString()
                    },
                    miners: minerAddresses,
                    validators: validatorAddresses
                };
                allSubnetInfo.push(formattedSubnet);
                console.log(`✅ Subnet ${id} info:`);
                console.dir(formattedSubnet, { depth: null });
            } catch (error) {
                console.error(`❌ Lỗi khi lấy thông tin subnet ${id}:`, error.message);
                if (error.info) console.error("Thông tin:", error.info);
            }
        }
        console.log("\n📦 Tổng số subnet hợp lệ:", allSubnetInfo.length);

        // Lấy thông tin chi tiết miner
        console.log("\nLấy thông tin chi tiết miner...");
        for (const subnet of allSubnetInfo) {
            try {
                const miners = await Promise.all(subnet.miners.map(async (addr) => {
                    try {
                        const miner = await modernTensor.getMinerInfo(addr);
                        return {
                            address: addr,
                            uid: miner.uid,
                            subnetUid: miner.subnet_uid.toString(),
                            stake: ethers.formatUnits(miner.stake, 18),
                            bitcoinStake: miner.bitcoin_stake.toString(),
                            scaledLastPerformance: (Number(miner.scaled_last_performance) / 1_000_000).toFixed(6),
                            scaledTrustScore: (Number(miner.scaled_trust_score) / 1_000_000).toFixed(6),
                            accumulatedRewards: ethers.formatUnits(miner.accumulated_rewards, 18),
                            lastUpdateTime: new Date(Number(miner.last_update_time) * 1000).toISOString(),
                            registrationTime: new Date(Number(miner.registration_time) * 1000).toISOString(),
                            status: miner.status === 0 ? "Inactive" : miner.status === 1 ? "Active" : "Jailed",
                            performanceHistoryHash: miner.performance_history_hash,
                            walletAddrHash: miner.wallet_addr_hash,
                            apiEndpoint: miner.api_endpoint,
                            owner: miner.owner
                        };
                    } catch (error) {
                        console.error(`Lỗi khi lấy thông tin miner ${addr}:`, error.message);
                        return null;
                    }
                }));
                console.log(`✅ Miner trong subnet ${subnet.subnetId}:`);
                console.dir(miners.filter(m => m !== null), { depth: null });
            } catch (error) {
                console.error(`❌ Lỗi khi lấy danh sách miner cho subnet ${subnet.subnetId}:`, error.message);
            }
        }

        // Lấy thông tin chi tiết validator
        console.log("\nLấy thông tin chi tiết validator...");
        for (const subnet of allSubnetInfo) {
            try {
                const validators = await Promise.all(subnet.validators.map(async (addr) => {
                    try {
                        const validator = await modernTensor.getValidatorInfo(addr);
                        return {
                            address: addr,
                            uid: validator.uid,
                            subnetUid: validator.subnet_uid.toString(),
                            stake: ethers.formatUnits(validator.stake, 18),
                            bitcoinStake: validator.bitcoin_stake.toString(),
                            scaledLastPerformance: (Number(validator.scaled_last_performance) / 1_000_000).toFixed(6),
                            scaledTrustScore: (Number(validator.scaled_trust_score) / 1_000_000).toFixed(6),
                            accumulatedRewards: ethers.formatUnits(validator.accumulated_rewards, 18),
                            lastUpdateTime: new Date(Number(validator.last_update_time) * 1000).toISOString(),
                            registrationTime: new Date(Number(validator.registration_time) * 1000).toISOString(),
                            status: validator.status === 0 ? "Inactive" : validator.status === 1 ? "Active" : "Jailed",
                            performanceHistoryHash: validator.performance_history_hash,
                            walletAddrHash: validator.wallet_addr_hash,
                            apiEndpoint: validator.api_endpoint,
                            owner: validator.owner
                        };
                    } catch (error) {
                        console.error(`Lỗi khi lấy thông tin validator ${addr}:`, error.message);
                        return null;
                    }
                }));
                console.log(`✅ Validator trong subnet ${subnet.subnetId}:`);
                console.dir(validators.filter(v => v !== null), { depth: null });
            } catch (error) {
                console.error(`❌ Lỗi khi lấy danh sách validator cho subnet ${subnet.subnetId}:`, error.message);
            }
        }
    } catch (error) {
        console.error("❌ Lỗi trong quá trình thực thi:", error.message);
        if (error.info) console.error("Thông tin:", error.info);
        console.log("Gợi ý: Đảm bảo ABI khớp với hợp đồng, tài khoản là owner để tạo subnet, và có đủ tCORE.");
    }
}

main().catch((error) => {
    console.error("Lỗi:", error);
    process.exitCode = 1;
});