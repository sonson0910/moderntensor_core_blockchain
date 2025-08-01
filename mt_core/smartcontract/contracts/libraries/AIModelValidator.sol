// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title AIModelValidator
 * @dev Advanced library for AI model quality assessment and validation
 * Implements sophisticated metrics for decentralized AI training evaluation
 */
library AIModelValidator {
    // Model quality thresholds
    uint256 constant MIN_ACCURACY_THRESHOLD = 5000; // 50% in basis points
    uint256 constant MAX_LOSS_THRESHOLD = 10000e18; // Maximum acceptable loss
    uint256 constant MIN_TRAINING_TIME = 300; // 5 minutes minimum
    uint256 constant MAX_TRAINING_TIME = 86400; // 24 hours maximum

    // Performance metrics weights (basis points)
    uint256 constant ACCURACY_WEIGHT = 4000; // 40%
    uint256 constant LOSS_WEIGHT = 2000; // 20%
    uint256 constant EFFICIENCY_WEIGHT = 1500; // 15%
    uint256 constant CONSISTENCY_WEIGHT = 1500; // 15%
    uint256 constant INNOVATION_WEIGHT = 1000; // 10%

    struct ModelMetrics {
        uint256 accuracy; // Model accuracy in basis points (0-10000)
        uint256 precision; // Precision metric in basis points
        uint256 recall; // Recall metric in basis points
        uint256 f1Score; // F1 score in basis points
        uint256 loss; // Training loss * 1e18
        uint256 trainingTime; // Time spent training in seconds
        uint256 computeEfficiency; // Operations per second
        uint256 memoryUsage; // Memory usage in bytes
        uint256 modelSize; // Model size in bytes
        uint256 convergenceRate; // How quickly model converged
    }

    struct ValidationResults {
        uint256 overallScore; // Overall quality score (0-10000)
        uint256 accuracyScore; // Accuracy component score
        uint256 efficiencyScore; // Efficiency component score
        uint256 consistencyScore; // Consistency component score
        uint256 innovationScore; // Innovation component score
        bool isPassing; // Whether model meets minimum requirements
        string[] warnings; // Validation warnings
        bytes32 validationHash; // Hash of validation process
    }

    struct ModelComparison {
        address betterModel; // Address of superior model
        uint256 improvementRatio; // Improvement ratio in basis points
        string[] strengths; // Areas where model excels
        string[] weaknesses; // Areas needing improvement
    }

    /**
     * @dev Comprehensive model quality assessment
     * @param metrics Model performance metrics
     * @param benchmarkMetrics Benchmark metrics for comparison
     * @param specializationType Type of AI specialization (0=Foundation, 1=Language, etc.)
     * @return ValidationResults Complete validation results
     */
    function validateModelQuality(
        ModelMetrics memory metrics,
        ModelMetrics memory benchmarkMetrics,
        uint256 specializationType
    ) internal pure returns (ValidationResults memory) {
        ValidationResults memory results;

        // Calculate component scores
        results.accuracyScore = calculateAccuracyScore(
            metrics,
            benchmarkMetrics
        );
        results.efficiencyScore = calculateEfficiencyScore(
            metrics,
            benchmarkMetrics
        );
        results.consistencyScore = calculateConsistencyScore(
            metrics,
            benchmarkMetrics
        );
        results.innovationScore = calculateInnovationScore(
            metrics,
            benchmarkMetrics,
            specializationType
        );

        // Calculate weighted overall score
        results.overallScore =
            (results.accuracyScore *
                ACCURACY_WEIGHT +
                (10000 - normalizedLoss(metrics.loss)) *
                LOSS_WEIGHT +
                results.efficiencyScore *
                EFFICIENCY_WEIGHT +
                results.consistencyScore *
                CONSISTENCY_WEIGHT +
                results.innovationScore *
                INNOVATION_WEIGHT) /
            10000;

        // Determine if model passes minimum requirements
        results.isPassing = isModelPassing(metrics, results.overallScore);

        // Generate validation hash
        results.validationHash = generateValidationHash(metrics, results);

        return results;
    }

    /**
     * @dev Calculate accuracy-based score with domain-specific adjustments
     * @param metrics Current model metrics
     * @param benchmark Benchmark metrics for comparison
     * @return uint256 Accuracy score (0-10000)
     */
    function calculateAccuracyScore(
        ModelMetrics memory metrics,
        ModelMetrics memory benchmark
    ) internal pure returns (uint256) {
        // Base accuracy score
        uint256 baseScore = metrics.accuracy;

        // Precision-Recall balance bonus
        uint256 prBonus = calculatePrecisionRecallBalance(
            metrics.precision,
            metrics.recall
        );

        // F1 score bonus
        uint256 f1Bonus = metrics.f1Score > benchmark.f1Score
            ? ((metrics.f1Score - benchmark.f1Score) * 1000) / benchmark.f1Score
            : 0;

        // Combined score with bonuses (capped at 10000)
        uint256 combinedScore = baseScore + prBonus + f1Bonus;
        return combinedScore > 10000 ? 10000 : combinedScore;
    }

    /**
     * @dev Calculate computational efficiency score
     * @param metrics Current model metrics
     * @param benchmark Benchmark metrics for comparison
     * @return uint256 Efficiency score (0-10000)
     */
    function calculateEfficiencyScore(
        ModelMetrics memory metrics,
        ModelMetrics memory benchmark
    ) internal pure returns (uint256) {
        // Training time efficiency (lower is better)
        uint256 timeEfficiency = (benchmark.trainingTime * 10000) /
            metrics.trainingTime;
        timeEfficiency = timeEfficiency > 15000
            ? 10000
            : (timeEfficiency * 2) / 3;

        // Compute efficiency (higher is better)
        uint256 computeRatio = (metrics.computeEfficiency * 10000) /
            benchmark.computeEfficiency;
        computeRatio = computeRatio > 20000 ? 10000 : computeRatio / 2;

        // Memory efficiency (lower usage is better)
        uint256 memoryEfficiency = (benchmark.memoryUsage * 10000) /
            metrics.memoryUsage;
        memoryEfficiency = memoryEfficiency > 15000
            ? 10000
            : (memoryEfficiency * 2) / 3;

        // Model size efficiency (smaller models preferred)
        uint256 sizeEfficiency = (benchmark.modelSize * 10000) /
            metrics.modelSize;
        sizeEfficiency = sizeEfficiency > 20000 ? 10000 : sizeEfficiency / 2;

        // Weighted efficiency score
        return
            (timeEfficiency *
                4 +
                computeRatio *
                3 +
                memoryEfficiency *
                2 +
                sizeEfficiency *
                1) / 10;
    }

    /**
     * @dev Calculate model consistency and stability score
     * @param metrics Current model metrics
     * @param benchmark Benchmark metrics for comparison
     * @return uint256 Consistency score (0-10000)
     */
    function calculateConsistencyScore(
        ModelMetrics memory metrics,
        ModelMetrics memory benchmark
    ) internal pure returns (uint256) {
        // Convergence rate score (faster convergence is better)
        uint256 convergenceScore = metrics.convergenceRate >
            benchmark.convergenceRate
            ? ((metrics.convergenceRate - benchmark.convergenceRate) * 5000) /
                benchmark.convergenceRate +
                5000
            : 5000;

        // Loss stability (lower loss variance indicates better stability)
        uint256 lossStability = metrics.loss <= benchmark.loss
            ? 8000 + ((benchmark.loss - metrics.loss) * 2000) / benchmark.loss
            : 8000 - ((metrics.loss - benchmark.loss) * 3000) / benchmark.loss;

        // Training time consistency (reasonable training time gets higher score)
        uint256 timeConsistency = 10000;
        if (metrics.trainingTime < MIN_TRAINING_TIME) {
            timeConsistency = 5000; // Too fast might indicate insufficient training
        } else if (metrics.trainingTime > MAX_TRAINING_TIME) {
            timeConsistency = 6000; // Too slow indicates inefficiency
        }

        return (convergenceScore + lossStability + timeConsistency) / 3;
    }

    /**
     * @dev Calculate innovation and uniqueness score
     * @param metrics Current model metrics
     * @param benchmark Benchmark metrics for comparison
     * @param specializationType AI domain specialization
     * @return uint256 Innovation score (0-10000)
     */
    function calculateInnovationScore(
        ModelMetrics memory metrics,
        ModelMetrics memory benchmark,
        uint256 specializationType
    ) internal pure returns (uint256) {
        uint256 innovationScore = 5000; // Base innovation score

        // Novel architecture bonus (smaller model with better performance)
        if (
            metrics.modelSize < benchmark.modelSize &&
            metrics.accuracy > benchmark.accuracy
        ) {
            innovationScore += 2000;
        }

        // Efficiency breakthrough bonus
        if (metrics.computeEfficiency > benchmark.computeEfficiency * 2) {
            innovationScore += 1500;
        }

        // Domain-specific innovation bonuses
        if (specializationType == 0) {
            // Foundation models
            // Bonus for general-purpose performance
            if (metrics.f1Score > (benchmark.f1Score * 110) / 100) {
                innovationScore += 1000;
            }
        } else if (specializationType == 1) {
            // Language models
            // Bonus for language-specific metrics
            if (metrics.precision > (benchmark.precision * 115) / 100) {
                innovationScore += 1000;
            }
        } else if (specializationType == 2) {
            // Vision models
            // Bonus for vision-specific accuracy
            if (metrics.accuracy > (benchmark.accuracy * 105) / 100) {
                innovationScore += 1000;
            }
        }

        return innovationScore > 10000 ? 10000 : innovationScore;
    }

    /**
     * @dev Check if model meets minimum requirements
     * @param metrics Model performance metrics
     * @param overallScore Calculated overall score
     * @return bool True if model passes all requirements
     */
    function isModelPassing(
        ModelMetrics memory metrics,
        uint256 overallScore
    ) internal pure returns (bool) {
        return (metrics.accuracy >= MIN_ACCURACY_THRESHOLD &&
            metrics.loss <= MAX_LOSS_THRESHOLD &&
            metrics.trainingTime >= MIN_TRAINING_TIME &&
            metrics.trainingTime <= MAX_TRAINING_TIME &&
            overallScore >= 6000 && // 60% minimum overall score
            metrics.f1Score >= 4000); // 40% minimum F1 score
    }

    /**
     * @dev Compare two models and determine which is superior
     * @param metricsA Metrics for model A
     * @param metricsB Metrics for model B
     * @return ModelComparison Detailed comparison results
     */
    function compareModels(
        ModelMetrics memory metricsA,
        ModelMetrics memory metricsB,
        address modelAddressA,
        address modelAddressB
    ) internal pure returns (ModelComparison memory) {
        ModelComparison memory comparison;

        // Calculate overall scores for both models
        ModelMetrics memory benchmarkMetrics = ModelMetrics({
            accuracy: 7000,
            precision: 7000,
            recall: 7000,
            f1Score: 7000,
            loss: 2000e18,
            trainingTime: 3600,
            computeEfficiency: 1000,
            memoryUsage: 1000000000,
            modelSize: 100000000,
            convergenceRate: 100
        });

        ValidationResults memory resultsA = validateModelQuality(
            metricsA,
            benchmarkMetrics,
            0
        );
        ValidationResults memory resultsB = validateModelQuality(
            metricsB,
            benchmarkMetrics,
            0
        );

        if (resultsA.overallScore >= resultsB.overallScore) {
            comparison.betterModel = modelAddressA;
            comparison.improvementRatio = resultsA.overallScore > 0
                ? (resultsA.overallScore * 10000) / resultsB.overallScore
                : 10000;
        } else {
            comparison.betterModel = modelAddressB;
            comparison.improvementRatio = resultsB.overallScore > 0
                ? (resultsB.overallScore * 10000) / resultsA.overallScore
                : 10000;
        }

        return comparison;
    }

    /**
     * @dev Calculate precision-recall balance bonus
     * @param precision Model precision in basis points
     * @param recall Model recall in basis points
     * @return uint256 Balance bonus (0-1000)
     */
    function calculatePrecisionRecallBalance(
        uint256 precision,
        uint256 recall
    ) internal pure returns (uint256) {
        if (precision == 0 || recall == 0) return 0;

        uint256 ratio = precision > recall
            ? (recall * 10000) / precision
            : (precision * 10000) / recall;

        // Bonus increases with better balance (closer to 1:1 ratio)
        return (ratio * 1000) / 10000;
    }

    /**
     * @dev Normalize loss value to 0-10000 scale
     * @param loss Raw loss value
     * @return uint256 Normalized loss score (higher is better)
     */
    function normalizedLoss(uint256 loss) internal pure returns (uint256) {
        if (loss >= MAX_LOSS_THRESHOLD) return 0;
        return 10000 - (loss * 10000) / MAX_LOSS_THRESHOLD;
    }

    /**
     * @dev Generate cryptographic hash of validation process
     * @param metrics Model metrics used in validation
     * @param results Validation results
     * @return bytes32 Validation hash for integrity verification
     */
    function generateValidationHash(
        ModelMetrics memory metrics,
        ValidationResults memory results
    ) internal pure returns (bytes32) {
        return
            keccak256(
                abi.encodePacked(
                    metrics.accuracy,
                    metrics.precision,
                    metrics.recall,
                    metrics.f1Score,
                    metrics.loss,
                    metrics.trainingTime,
                    results.overallScore,
                    results.isPassing
                )
            );
    }

    /**
     * @dev Validate model against domain-specific requirements
     * @param metrics Model metrics
     * @param domainType AI domain (0=Foundation, 1=Language, 2=Vision, 3=Multimodal)
     * @return bool True if model meets domain requirements
     */
    function validateDomainSpecificRequirements(
        ModelMetrics memory metrics,
        uint256 domainType
    ) internal pure returns (bool) {
        if (domainType == 0) {
            // Foundation models
            return metrics.accuracy >= 6000 && metrics.f1Score >= 5500;
        } else if (domainType == 1) {
            // Language models
            return metrics.precision >= 7000 && metrics.recall >= 6500;
        } else if (domainType == 2) {
            // Vision models
            return metrics.accuracy >= 7500 && metrics.precision >= 7000;
        } else if (domainType == 3) {
            // Multimodal models
            return
                metrics.accuracy >= 6500 &&
                metrics.f1Score >= 6000 &&
                metrics.precision >= 6500;
        }

        return false; // Unknown domain type
    }
}
