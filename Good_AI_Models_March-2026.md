Finding the right OpenRouter model requires balancing API latency, token costs, and a lack of restrictive guardrails. Here are the fastest, most affordable models currently dominating the uncensored roleplay space:

### Top Affordable & Fast NSFW Roleplay Models

* **DeepSeek R1 (0528) & DeepSeek-V3.2**
* **The Vibe:** The reigning champions of cost-to-performance for uncensored roleplay.
* **Why it works:** They offer excellent reasoning and highly nuanced storytelling. They are incredibly cheap (around 0.45 USD per million input tokens) and practically ignore moderation guardrails. The R1 model occasionally outputs its "thinking" tokens, which can add a fascinating layer to an AI companion's internal monologue if you are fine-tuning Runa's thought processes.


* **Cydonia v4.3 (24B)**
* **The Vibe:** Fast, focused, and highly steerable.
* **Why it works:** This is a Mistral fine-tune built specifically from the ground up for roleplay. At 24B parameters, it runs blazingly fast and keeps API costs very low. It is great for dynamic storytelling and keeping track of complex character cards without the latency drag of massive frontier models.


* **WizardLM-2 8x22B**
* **The Vibe:** Heavyweight performance at mid-weight speeds.
* **Why it works:** While a bit larger, it utilizes a Mixture-of-Experts (MoE) architecture to keep inference fast. It is famously unmoderated and handles multi-character roleplay beautifully, making it a great engine for narrating expansive lore and keeping track of complex RPG mechanics within the Norse Saga Engine.


* **Mistral Nemo (12B) / UnslopNemo**
* **The Vibe:** Maximum speed and absolute lowest cost.
* **Why it works:** If you want rock-bottom costs for your Python backend, this 12B model punches well above its weight class. It is fully uncensored out of the box and handles conversational RP perfectly, though it might struggle slightly if you overload it with massive world-building lorebooks compared to the larger models above.



### A Quick Note on "Flagship" Models

If you decide to splurge occasionally, **Claude 3.5 Sonnet** and the newer **Claude 4.5** variants are incredible for creative writing, but they require a very solid jailbreak prompt to handle NSFW content and are significantly more expensive. **Gemini 3 Flash** is incredibly cheap and fast, but it can be finicky with explicit NSFW when accessed through the OpenRouter API rather than directly through Google's developer portal.

Would you like me to suggest specific API generation settings (like temperature, top_k, and Min-P) to get the most natural, uncensored responses out of these models?