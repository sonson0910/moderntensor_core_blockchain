# ModernTensor: Detailed Documentation on Operational Mechanisms and Core Formulas

**ModernTensor Development Team**
*(Last Updated: [Actual Update Date])*

## 1. Abstract

This document provides a comprehensive overview and detailed breakdown of the mathematical formulas and core operational mechanisms of ModernTensor – a decentralized Artificial Intelligence (AI) network built on the Cardano blockchain [source: 76, 79]. The presented mechanisms include incentive distribution, performance evaluation, penalty processing (implied, potentially detailed elsewhere), weighting calculations, resource allocation, and supplementary mechanisms like DAO governance [source: 77]. Each formula is clearly described using mathematical notation, accompanied by detailed explanations of its meaning, purpose, relevant parameters, and illustrative examples [source: 78]. This document specifically focuses on the underlying logic, assuming implementation details on Cardano (e.g., via Plutus smart contracts, transaction metadata, or off-chain components) are covered in separate architectural documents.

## 2. Introduction

ModernTensor is a decentralized AI network leveraging the power of the Cardano blockchain technology to create a transparent, fair, and efficient environment for training, validating, and rewarding AI models [source: 79]. Inspired by Bittensor, it adapts similar concepts to the Cardano ecosystem. This document focuses on analyzing the foundational formulas governing the economic, evaluation, and governance mechanisms of the system [source: 80]. The goal is to provide a deep understanding of the operational logic and design considerations behind ModernTensor.

## 3. Core Mechanisms

### 3.1. Incentive Distribution

The incentive mechanism is designed to ensure rewards are fairly distributed to participating entities (Miners and Validators) based on their contribution, performance, and reliability.

#### 3.1.1. Miner Incentive

The reward for a Miner ($Incentive_{miner}$) is calculated based on their trust score, weight, and performance scores from Validators.

**Formula:** [source: 81]
$Incentive_{miner}(x) = f(trust_{score}(x)) \times \frac{\sum_{j=0}^{m}(W_{x} \times P_{xj})}{\sum_{i=0}^{n}\sum_{j=0}^{m}(W_{i} \times P_{ij})}$

**Meaning:** This formula ensures that Miners with high performance and good reliability (reflected by `trust_score` and `P_xj`) receive deserving rewards, considering their weight ($W_x$) and normalized against the total contribution value of the entire system.

**Parameters:** [source: 82, 83]
* $trust_{score}(x)$: Historical trust score of Miner $x$.
* $f(trust_{score}(x))$: A function of the trust score (instead of direct multiplication) to adjust the reward sensitivity. *See Design Considerations.*
* $W_x$: Weight of Miner $x$ (can be based on stake, historical performance, or a combination). *See Formula 3.3.1.*
* $P_{xj}$: Performance score of Miner $x$ as evaluated by Validator $j$. *See Formula 3.2.5 (adjusted performance).*
* Denominator: The sum of weighted contribution values of all Miners in the system, used for normalization.

**Example:** (Assuming $f(trust) = trust$ as in the original formula [source: 84, 85])
Miner $x$ has $W_x=2$, $trust_{score}(x)=0.9$. Evaluated by 3 validators: $P_{x1}=0.8, P_{x2}=0.9, P_{x3}=0.7$. Total system value $\sum \sum (W_i \times P_{ij}) = 50$.
$Incentive_{miner}(x) = 0.9 \times \frac{2 \times (0.8 + 0.9 + 0.7)}{50} = 0.9 \times \frac{2 \times 2.4}{50} = 0.0864$

**Design Considerations (Miner Incentive):**
* **Trust Score Impact:** The original formula multiplies directly by `trust_score`. Consider using an increasing function $f(trust\_score)$ that "saturates" near 1.0 (e.g., sigmoid or a capped linear function) to reduce reward volatility for small trust score changes at high levels.
* **Weight Calculation $W_x$:** Determining Miner weight needs to balance historical performance and resistance to manipulation. *See section 3.3.1.*

#### 3.1.2. Validator Incentive

Validators ($Incentive_{validator}$) are rewarded based on their trust score, weight, and their own evaluation performance.

**Formula:** [source: 86]
$Incentive_{validator}(v) = f(trust_{score}(v)) \times \frac{W_{v} \times E_{v}}{\sum_{u \in V}(W_{u} \times E_{u})}$

**Meaning:** Incentivizes Validators to maintain high performance ($E_v$) and reliability ($trust_{score}$), with rewards proportional to their contribution (represented by $W_v$) relative to the entire Validator pool.

**Parameters:** [source: 87]
* $trust_{score}(v)$: Historical trust score of Validator $v$.
* $f(trust_{score}(v))$: Function adjusting the impact of trust score (similar to Miner).
* $W_v$: Weight of Validator $v$. *See Formula 3.3.2.*
* $E_v$: Performance score of Validator $v$. *See Formula 3.2.3.*
* Denominator: The sum of weighted contribution values of all Validators, used for normalization.

**Example:** (Assuming $f(trust) = trust$ as in the original formula)
Validator $v$ has $W_v=3$, $E_v=0.95$, $trust_{score}(v)=0.85$. Total Validator value $\sum (W_u \times E_u) = 60$.
$Incentive_{validator}(v) = 0.85 \times \frac{3 \times 0.95}{60} = 0.85 \times \frac{2.85}{60} \approx 0.0404$

**Design Considerations (Validator Incentive):**
* **Weight Calculation $W_v$:** The balance between stake and performance in $W_v$ is crucial. *See section 3.3.2.*

### 3.2. Performance Evaluation

The system uses multiple metrics to comprehensively evaluate the performance of Miners and Validators.

#### 3.2.1. Task Completion Rate ($Q_{task}$)

Measures the success rate of task completion, prioritizing recent tasks.

**Formula:** [source: 88]
$Q_{task} = \frac{\sum_{t}(task_{success,t} \times e^{-\delta(T-t)})}{\sum_{t}(task_{total,t} \times e^{-\delta(T-t)})}$

**Meaning:** Evaluates task completion efficiency, using an exponential decay function $e^{-\delta(T-t)}$ to reduce the weight of older tasks.

**Parameters:** [source: 88, 89]
* $task_{success,t}$: Number of tasks successfully completed at time $t$.
* $task_{total,t}$: Total number of tasks assigned at time $t$.
* $T$: Current time.
* $\delta$: Decay constant (e.g., 0.5), controlling the "forgetting" rate of old tasks. *This parameter could be governed by the DAO.*

**Example:** [source: 89, 90]
A miner has data: $t=1$: 8/10, $t=2$: 9/10, $t=3$: 10/10. With $T=3$, $\delta=0.5$.
Numerator $\approx 8 \times e^{-1} + 9 \times e^{-0.5} + 10 \times e^{0} \approx 18.407$
Denominator $\approx 10 \times e^{-1} + 10 \times e^{-0.5} + 10 \times e^{0} \approx 19.75$
$Q_{task} \approx 18.407 / 19.75 \approx 0.932$ (93.2%)

#### 3.2.2. Miner Approval Rate ($D_{miner}$)

Measures the frequency with which a Miner's work is approved by Validators.

**Formula:** [source: 91]
$D_{miner}(i) = \frac{\sum(\text{Number of times Miner } i \text{ was approved by Validators})}{\text{Total number of times Miner } i \text{ was audited}}$

**Meaning:** A simple indicator of the acceptance of the Miner's results by the validation network.

**Example:** [source: 91]
Miner $i$ is audited 10 times, approved 8 times: $D_{miner}(i) = 8 / 10 = 0.8$ (80%).

#### 3.2.3. Validator Performance Score ($E_{validator}$)

Evaluates the overall performance of a Validator based on multiple factors.

**Original Formula:** [source: 92]
$E_{validator} = \theta_1 Q_{task\_validator} + \theta_2 accuracy_{validator} + \theta_3 \times e^{-k \frac{|Eval - Avg|}{\sigma}}$

**Meaning:** Combines task completion ability ($Q_{task}$ of the validator itself if they also perform tasks), accuracy in evaluating Miners ($accuracy$), and the level of consensus with other Validators (the $e^{-k...}$ component penalizes evaluations deviating significantly from the average $Avg$).

**Parameters:** [source: 93]
* $\theta_1, \theta_2, \theta_3$: Weight coefficients ($\sum \theta_i = 1$). *Could be governed by the DAO.*
* $Q_{task\_validator}$: Task completion rate of the Validator itself (if applicable).
* $accuracy_{validator}$: Accuracy of the Validator's evaluations. *Needs clear definition of measurement.*
* $Eval$: The current Validator's evaluation score.
* $Avg$: The average evaluation score of all Validators for the same subject.
* $\sigma$: Standard deviation of the evaluation scores.
* $k$: Coefficient controlling the penalty level for deviation. *Could be governed by the DAO.*

**Example:** [source: 94, 95]
Assume $Q_{task}=0.9, accuracy=0.85, \frac{|Eval-Avg|}{\sigma}=0.2, k=1, \theta_1=0.4, \theta_2=0.3, \theta_3=0.3$.
$E_{validator} = 0.4 \times 0.9 + 0.3 \times 0.85 + 0.3 \times e^{-0.2} \approx 0.36 + 0.255 + 0.245 = 0.86$

**Design Considerations (Validator Performance):**
* **Measuring `accuracy_validator`:** This is challenging. An objective method is needed, e.g., based on historical consistency, consensus with reputable validators, or using "honeypot tasks" with known outcomes.
* **Deviation Penalty Component:** The `exp(-k * dev)` mechanism might be too sensitive. Consider other penalty functions (e.g., linear penalty beyond a certain threshold) or comparing only against the most trusted validator group. The parameter `k` and coefficients `θ` should be reviewed by the DAO.

#### 3.2.4. Basic Miner Performance ($P_{miner}$)

Similar to $Q_{task}$, measures the Miner's task completion performance with time-decay weighting.

**Formula:** [source: 96] (Identical to $Q_{task}$ formula [source: 88])
$P_{miner} = \frac{\sum_{t}(task_{success,t} \times e^{-\delta(T-t)})}{\sum_{t}(task_{total,t} \times e^{-\delta(T-t)})}$

**Meaning, Parameters, Example:** Similar to section 3.2.1.

#### 3.2.5. Adjusted Miner Performance ($P_{miner\_adjusted}$)

Adjusts the Miner's performance score based on the reliability of the Validators who evaluated them.

**Formula:** [source: 98]
$P_{miner\_adjusted} = \frac{\sum_{v}(trust_{score_{v}} \times P_{miner,v})}{\sum_{v}trust_{score_{v}}}$

**Meaning:** Minimizes the impact of evaluations from low-trust Validators, increasing the reliability of the final performance score. This is a key input for the consensus mechanism.

**Parameters:** [source: 99, 100]
* $trust_{score_v}$: Trust score of Validator $v$.
* $P_{miner,v}$: Performance score of the Miner as evaluated by Validator $v$.

**Example:** [source: 100, 101]
Miner M1 is evaluated by V1 ($trust=0.8$) with $P_{miner,1}=0.9$, and V2 ($trust=0.5$) with $P_{miner,2}=0.7$.
$P_{miner\_adjusted} = \frac{(0.8 \times 0.9) + (0.5 \times 0.7)}{0.8 + 0.5} = \frac{0.72 + 0.35}{1.3} \approx 0.823$

### 3.3. Participant Weight Calculation

Weights reflect the "importance" or "influence" of Miners and Validators in the system, affecting rewards and other mechanisms.

#### 3.3.1. Miner Weight ($W_x$)

Calculated based on historical performance, prioritizing recent values.

**Formula:** [source: 102]
$W_x = \sum_{t} P_{miner\_adjusted,t} \times e^{-\delta(T-t)}$
*(Note: Using $P_{miner\_adjusted}$ instead of the basic $P_{miner}$ seems more consistent with using trust-weighted scores).*

**Meaning:** Aggregates the Miner's historical adjusted performance, encouraging sustained high and stable performance as recent performance has a greater impact.

**Parameters:** [source: 102]
* $P_{miner\_adjusted,t}$: Adjusted performance of the Miner at time $t$.
* $T$: Current time.
* $\delta$: Decay constant (e.g., 0.5). *Could be governed by the DAO.*

**Example:** [source: 103, 104] (Using adjusted scores)
Miner has adjusted performance: $t=1: 0.8, t=2: 0.9, t=3: 1.0$. With $T=3, \delta=0.5$.
$W_x = 0.8 \times e^{-1} + 0.9 \times e^{-0.5} + 1.0 \times e^{0} \approx 0.294 + 0.546 + 1.0 = 1.84$

#### 3.3.2. Validator Weight ($W_{validator}$)

Combines stake amount, performance, and participation time.

**Formula:** [source: 119]
$W_{validator} = \lambda \times \frac{stake_v}{\sum stake} + (1 - \lambda) \times E_{validator} \times (1 + log(time\_participated))$

**Meaning:** Balances financial contribution (stake) and quality contribution (performance $E_{validator}$), while also recognizing long-term commitment through participation time ($time\_participated$).

**Parameters:** [source: 119]
* $stake_v$: Stake amount of Validator $v$.
* $\sum stake$: Total stake of all Validators.
* $E_{validator}$: Performance score of Validator $v$. *See Formula 3.2.3.*
* $time\_participated$: Time Validator $v$ has participated in the system (unit needs clear definition).
* $\lambda$: Balancing coefficient (0 to 1), determining the weight between stake and performance/time. *Crucial parameter, should be governed by the DAO.*
* $log()$: Logarithm function (natural or base 10) to provide diminishing returns for participation time.

**Example:** [source: 120]
Assume $stake_v=500, \sum stake=2000, E_{validator}=0.9, time=10$ (arbitrary units), $\lambda=0.5$. Using $log_{10}$:
$W_{validator} = 0.5 \times \frac{500}{2000} + (1 - 0.5) \times 0.9 \times (1 + log_{10}(10))$
$W_{validator} = 0.5 \times 0.25 + 0.5 \times 0.9 \times (1 + 1) = 0.125 + 0.5 \times 0.9 \times 2 = 0.125 + 0.9 = 1.025$
*(Note: The original example [source: 120] might have used natural log or different calculation, yielding 0.71)*

**Design Considerations (Validator Weight):**
* **Parameter `lambda`:** Deciding the stake/performance balance is critical and should be carefully governed by the community (DAO).
* **Performance Normalization:** Consider using relative $E_{validator}$ (divided by network average) instead of absolute value.
* **Tiered Stake:** Could consider different multipliers for the stake component based on stake tiers, rather than a purely linear ratio, to reduce the advantage of excessively large stakes.

### 3.4. Trust Score & Fairness Mechanism

The system manages reputation (trust score) and ensures fair participation opportunities for Miners.

#### 3.4.1. Trust Score Update

Trust scores are updated periodically, considering new performance and decay due to inactivity.

**Formula:** [source: 105]
$TrustScore_{new} = TrustScore_{old} \times e^{-\delta_{trust} \times time\_since\_last\_evaluation} + \alpha \times f_{update}(Score_{new})$

**Meaning:** Reduces trust score over time if not evaluated (encouraging active participation) and updates based on the latest performance score ($Score_{new}$) with a learning rate ($\alpha$).

**Parameters:** [source: 105, 106]
* $TrustScore_{old/new}$: Old/new trust score.
* $\delta_{trust}$: Decay constant specific to trust score (e.g., 0.1). *Could be governed by the DAO.*
* $time\_since\_last\_evaluation$: Number of cycles/time since the last evaluation.
* $\alpha$: Learning rate (e.g., 0.1). *Could be governed by the DAO, or dynamic.*
* $Score_{new}$: The new performance score received (e.g., $P_{miner\_adjusted}$ or $E_{validator}$). If not evaluated in the cycle, $Score_{new}=0$. [source: 107]
* $f_{update}(Score_{new})$: Mapping function for the new score before updating (e.g., linear or sigmoid). *See Design Considerations.*

**Example:** [source: 107, 108]
Miner M5 has $TrustScore_{old}=0.5$, was not selected for 2 cycles ($time=2$), $\delta_{trust}=0.1, \alpha=0.1, Score_{new}=0$.
$TrustScore_{new} = 0.5 \times e^{-0.1 \times 2} + 0.1 \times 0 = 0.5 \times e^{-0.2} \approx 0.5 \times 0.8187 \approx 0.409$

**Design Considerations (Trust Update):**
* **Parameters $\delta_{trust}, \alpha$:** The choice of these values significantly impacts the speed of reputation change. Should allow DAO adjustment. Consider dynamic `alpha` based on current trust level.
* **Function $f_{update}(Score_{new})$:** Instead of linear addition `alpha * Score_new`, a non-linear function could limit the impact of sudden score spikes.
* **Linkage of `Score_new`:** Needs clarity on exactly where `Score_new` comes from ($P_{miner\_adjusted}$ or another source).

#### 3.4.2. Miner Selection Probability

Increases the selection chance for Miners who haven't been selected recently to ensure fairness.

**Formula:** [source: 109]
$SelectionProbability = trust\_score \times (1 + \beta \times \min(time\_since\_last\_selection, MaxTimeBonusEffect))$

**Meaning:** Base selection probability relies on `trust_score`, but is boosted by a fairness bonus ($\beta$) proportional to the time since last selection, capped by `MaxTimeBonusEffect`.

**Parameters:** [source: 110]
* $trust\_score$: Current trust score of the Miner.
* $\beta$: Fairness bonus coefficient (e.g., 0.2). *Could be governed by the DAO.*
* $time\_since\_last\_selection$: Number of cycles/time since the Miner was last selected.
* $MaxTimeBonusEffect$: Maximum number of cycles the time bonus applies (e.g., 10). *Prevents infinite bonus increase.*

### 3.5. Consensus Mechanism

The consensus mechanism in ModernTensor ensures the network achieves agreement on the performance and contribution value of Miners, forming the basis for reward distribution and maintaining service quality. This process relies on continuous evaluation by Validators.

#### 3.5.1. Evaluation Process

*   **Query Issuance:** Validators periodically send queries (prompts) or test tasks to Miners within the network (or a specific subnet).
*   **Response Assessment:** Validators evaluate Miner responses based on predefined criteria, which may include:
    *   Accuracy/quality of the result (e.g., comparison against a reference result or structured subjective scoring).
    *   Response latency.
    *   Resource consumption (if measurable).
*   **Scoring:** Based on these criteria, the Validator assigns a performance score to each Miner they interacted with during that cycle ($P_{miner,v}$ as used in Formula 3.2.5).

#### 3.5.2. Evaluation Aggregation and Weighting

*   **Gathering Evaluations:** Performance scores ($P_{miner,v}$) from multiple Validators for the same Miner are collected.
*   **Calculating Adjusted Score:** The Miner's final adjusted performance score ($P_{miner\_adjusted}$) is calculated by taking a weighted average of the received evaluations, using the Validators' trust scores as weights (as per Formula 3.2.5). This ensures evaluations from more reputable Validators have a greater impact.
    $P_{miner\_adjusted} = \frac{\sum_{v}(trust_{score_{v}} \times P_{miner,v})}{\sum_{v}trust_{score_{v}}}$

    **Example:**
    Assume Miner M1 is evaluated by three Validators:
    *   Validator V1 ($trust_{score_{V1}} = 0.9$) gives score $P_{M1,V1} = 0.85$.
    *   Validator V2 ($trust_{score_{V2}} = 0.7$) gives score $P_{M1,V2} = 0.80$.
    *   Validator V3 ($trust_{score_{V3}} = 0.5$) gives score $P_{M1,V3} = 0.60$ (Perhaps V3 is less reliable or has different criteria).

    The adjusted performance score for Miner M1 is calculated as:
    $P_{M1\_adjusted} = \frac{(0.9 \times 0.85) + (0.7 \times 0.80) + (0.5 \times 0.60)}{0.9 + 0.7 + 0.5}$
    $P_{M1\_adjusted} = \frac{0.765 + 0.560 + 0.300}{2.1} = \frac{1.625}{2.1} \approx 0.774$

    Notice how the evaluation from the lowest-trust Validator (V3) has less impact on the final adjusted score compared to the higher-trust Validators (V1 and V2).

#### 3.5.3. Network State Update

*   **Miner Ranking:** Based on $P_{miner\_adjusted}$ and other factors (like stake, weight $W_x$), the network can establish a ranking of Miners.
*   **Impact on Rewards/Stake:** This consensus outcome directly influences:
    *   Incentive Distribution: As defined in Formula 3.1.1.
    *   Trust Score Updates: As defined in Formula 3.4.1.
    *   (Potentially) Stake adjustments or penalty mechanisms if performance is consistently low or malicious behavior is detected.

*(Note: The specific details of how evaluations and state are stored and processed on Cardano (e.g., using Datum in UTxOs, transaction metadata, or off-chain solutions) would be described in more detailed architectural documentation.)*

*(Further sections like Penalty Mechanisms, Resource Allocation, DAO Governance would follow a similar structure if detailed formulas exist.)*

---
*(Disclaimer: The formulas and mechanisms described are based on provided source references and standard practices in similar decentralized networks. Specific implementation details and parameter tuning in ModernTensor may vary.)*
