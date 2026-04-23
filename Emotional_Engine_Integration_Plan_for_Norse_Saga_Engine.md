\# \*\*Emotional Engine Integration Plan for Norse Saga Engine\*\*

\#\# \*\*Overview\*\*

The proposed emotional system adds a \*\*deterministic, tunable\*\* layer that models how characters process emotions based on:  
\- \*\*MBTI T/F axis\*\* (continuous cognitive-emotional weighting)  
\- \*\*Gender-linked tendencies\*\* (as averages, not absolutes)  
\- \*\*Individual variance\*\* (dominant over averages)  
\- \*\*Existing systems\*\* (fear, chronotype, stress, rituals)

The system is designed to be \*\*non-stereotyping\*\*, \*\*psychologically accurate\*\*, and \*\*fully integrated\*\* with the current Norse Saga Engine architecture.

\---

\#\# \*\*Staged Implementation Plan\*\*

\#\#\# \*\*Phase 1: Data Structures & Character Profiles\*\*    
\*\*Goal\*\*: Add emotional profile fields to character YAML files and create runtime data structures.

\#\#\#\# \*\*1.1 Extend Character YAML Schema\*\*  
Add an \`emotion\_profile\` section to all character files (player characters, NPCs, bondmaids, villains). Example:

\`\`\`yaml  
emotion\_profile:  
  tf\_axis: 0.65                \# 0.0 (Thinking) to 1.0 (Feeling)  
  gender\_axis: \-0.2             \# \-1.0 (male-leaning) to \+1.0 (female-leaning)  
  individual\_offset: 0.05        \# small random variance  
  baseline\_intensity: 1.0        \# overall emotional reactivity multiplier  
  expression\_threshold: 0.6      \# minimum intensity to show emotion externally  
  rumination\_bias: 0.4           \# how much they dwell (0-1)  
  decay\_rate: 0.08               \# base decay per turn  
  channel\_weights:               \# per-emotion sensitivity  
    fear: 1.0  
    anger: 0.8  
    sadness: 0.7  
    joy: 0.9  
    shame: 0.6  
    attachment: 1.0  
\`\`\`

\*\*Code Changes\*\*:  
\- Update \`data/character\_schema.yaml\` (or equivalent) to include these fields.  
\- Modify \`generators/character\_generator.py\` to generate random emotional profiles (using normal distribution around means).  
\- Update \`session/entity\_canonizer.py\` to include emotional profile stubs for auto-generated characters.

\#\#\#\# \*\*1.2 Runtime Emotional State in GameState\*\*  
Add an \`emotional\_state\` dictionary to \`GameState\` to track current emotional intensities per channel.

\`\`\`python  
@dataclass  
class EmotionalState:  
    fear: float \= 0.0  
    anger: float \= 0.0  
    sadness: float \= 0.0  
    joy: float \= 0.0  
    shame: float \= 0.0  
    attachment: float \= 0.0  
    last\_update: int \= 0  \# turn count

@dataclass  
class GameState:  
    \# ... existing fields ...  
    player\_emotional\_state: EmotionalState \= field(default\_factory=EmotionalState)  
    npc\_emotional\_states: Dict\[str, EmotionalState\] \= field(default\_factory=dict)  
\`\`\`

Also add a field to track \*\*stress accumulation\*\* (linked to suppression) and \*\*chronotype effects\*\*.

\#\#\#\# \*\*1.3 Load Emotional Profiles\*\*  
Modify \`data\_system.py\` to load emotional profile data into character dicts. Ensure backward compatibility (if missing, assign defaults).

\---

\#\#\# \*\*Phase 2: Core Emotional Engine\*\*    
\*\*Goal\*\*: Implement the mathematical model for emotional impact, decay, and expression.

\#\#\#\# \*\*2.1 New Module: \`systems/emotional\_engine.py\`\*\*  
Create a dedicated module with classes/functions:

\`\`\`python  
\# systems/emotional\_engine.py

class EmotionalEngine:  
    def \_\_init\_\_(self, character\_profile: dict):  
        self.profile \= character\_profile  
        self.state \= EmotionalState()

    def compute\_impact(self, stimulus: str, stimulus\_strength: float, channel: str) \-\> float:  
        """Compute final emotional impact for a given stimulus."""  
        raw \= stimulus\_strength \* self.profile\['channel\_weights'\].get(channel, 1.0)

        \# T/F modifier  
        tf\_mod \= lerp(0.85, 1.15, self.profile\['tf\_axis'\])

        \# Gender modifier (small)  
        gender\_mod \= lerp(0.9, 1.1, (self.profile\['gender\_axis'\] \+ self.profile\['individual\_offset'\]) / 2\)

        \# Personality modifiers (Big Five) \- to be integrated later  
        \# For now, just use baseline intensity  
        final \= raw \* tf\_mod \* gender\_mod \* self.profile\['baseline\_intensity'\]  
        return final

    def update\_state(self, channel: str, impact: float, turn: int):  
        """Apply impact and decay to a channel."""  
        \# Decay  
        decay \= self.profile\['decay\_rate'\] \- (self.profile\['rumination\_bias'\] \* impact)  
        self.state\[channel\] \= max(0, self.state\[channel\] \- decay \+ impact)

    def should\_express(self, channel: str) \-\> bool:  
        """Check if emotion exceeds expression threshold."""  
        return self.state\[channel\] \> self.profile\['expression\_threshold'\]

    def internalize(self, channel: str) \-\> float:  
        """Return stress contribution from internalized emotion."""  
        \# Suppressed emotions feed stress (to be used by stress system)  
        return self.state\[channel\] \* 0.1  \# example scaling  
\`\`\`

\#\#\#\# \*\*2.2 Integrate with Turn Processing\*\*  
In \`engine.py\`, after receiving AI narrative, we need to \*\*extract emotional stimuli\*\* from the narrative and player input. This is the hardest part. Options:  
\- Use regex patterns for emotion keywords (anger, fear, etc.) with intensity multipliers.  
\- Use an AI call (via Yggdrasil) to analyze the narrative for emotional content (more accurate but costly).  
\- Start with keyword-based extraction, then enhance later.

Add a method \`\_extract\_emotional\_stimuli(narrative: str, player\_input: str)\` that returns a dict of \`{channel: strength}\`. Example keywords:

\`\`\`python  
EMOTION\_KEYWORDS \= {  
    'fear': \['fear', 'afraid', 'terrified', 'dread', 'horror', 'panic'\],  
    'anger': \['anger', 'angry', 'rage', 'fury', 'wrath', 'irritated'\],  
    'sadness': \['sad', 'grief', 'sorrow', 'despair', 'mourn'\],  
    'joy': \['joy', 'happy', 'delight', 'pleasure', 'content'\],  
    'shame': \['shame', 'guilt', 'embarrass', 'humiliate', 'disgrace'\],  
    'attachment': \['love', 'loyal', 'trust', 'bond', 'friend', 'ally'\]  
}  
\`\`\`

For each occurrence, add strength based on word frequency or intensity modifiers (e.g., "terrified" \> "afraid").

Then, in \`process\_action()\`, after the AI response (or before, depending on whether we want emotions to influence the AI), call \`\_update\_emotional\_states(stimuli)\`.

\#\#\#\# \*\*2.3 Emotional State Update Loop\*\*  
For player and each NPC present:

\`\`\`python  
def \_update\_emotional\_states(self, stimuli: Dict\[str, float\]):  
    \# Player  
    player\_engine \= EmotionalEngine(self.state.player\_character\['emotion\_profile'\])  
    for ch, strength in stimuli.items():  
        impact \= player\_engine.compute\_impact('narrative', strength, ch)  
        player\_engine.update\_state(ch, impact, self.state.turn\_count)  
        if player\_engine.should\_express(ch):  
            \# Optionally mark that emotion was expressed (for logging)  
            pass  
        else:  
            \# Add stress  
            stress \= player\_engine.internalize(ch)  
            self.state.player\_stress \+= stress  \# need a stress field

    self.state.player\_emotional\_state \= player\_engine.state

    \# NPCs similarly  
    for npc in self.state.npcs\_present:  
        npc\_id \= npc\['id'\]  
        npc\_engine \= EmotionalEngine(npc\['emotion\_profile'\])  
        \# ... same loop ...  
        self.state.npc\_emotional\_states\[npc\_id\] \= npc\_engine.state  
\`\`\`

We also need to handle \*\*decay\*\* even without new stimuli: call \`decay\_all()\` each turn.

\---

\#\#\# \*\*Phase 3: Prompt Integration\*\*    
\*\*Goal\*\*: Inject emotional context into the AI system prompt to influence narration.

\#\#\#\# \*\*3.1 Add Emotional Context Layer\*\*  
In \`prompt\_builder.py\`, add a new layer (e.g., between Myth Engine and Yggdrasil) that outputs:

\`\`\`  
\=== EMOTIONAL STATE \===  
Player: fear 0.3 (simmering), anger 0.1 (calm), joy 0.7 (content)...  
NPC Thorbjorn: anger 0.6 (agitated), attachment 0.2 (distant)...  
\`\`\`

Format using natural language based on intensity thresholds.

\#\#\#\# \*\*3.2 Include Emotional Profile in Character Descriptions\*\*  
When building NPC profiles (layer 6), append emotional tendencies:

\`\`\`  
NPC: Thorbjorn — male — Blacksmith — karl  
Emotional nature: Thinking-leaning, slightly male-typical, slow to anger but intense when roused.  
\`\`\`

This can be generated from the emotional profile (e.g., high tf\_axis → "feeling-leaning", etc.).

\#\#\#\# \*\*3.3 Influence Narration with Emotional State\*\*  
Add instructions to the core roleplay rules: "Consider the emotional states of characters when narrating their actions, dialogue, and reactions."

\---

\#\#\# \*\*Phase 4: Behavioral Mapping\*\*    
\*\*Goal\*\*: Use emotional states to influence NPC decision-making and player character automation (if desired).

\#\#\#\# \*\*4.1 Emotion → Behavior Probability Tables\*\*  
Implement the precomputed behavior tables as described in the design doc. Store per character in memory or generate on the fly.

Add to \`emotional\_engine.py\`:

\`\`\`python  
class EmotionalBehavior:  
    BEHAVIOR\_TABLE \= {  
        'fear': \[  
            ('flee', 0.35), ('hide', 0.30), ('defensive\_posture', 0.25), ('ritual\_retreat', 0.10)  
        \],  
        'anger': \[  
            ('confront', 0.40), ('passive\_aggression', 0.30), ('ritual\_release', 0.20), ('withdrawal', 0.10)  
        \],  
        \# ...  
    }

    @staticmethod  
    def choose\_behavior(channel: str, intensity: float, personality\_mods: dict) \-\> str:  
        """Return a behavior based on weighted probabilities."""  
        behaviors \= EmotionalBehavior.BEHAVIOR\_TABLE\[channel\]  
        \# Apply modifiers (e.g., extraversion increases confront)  
        \# Normalize probabilities  
        \# Return sampled behavior  
\`\`\`

\#\#\#\# \*\*4.2 Integrate with Yggdrasil / NPC Decision-Making\*\*  
When the AI needs to decide an NPC's action (e.g., in combat or social interaction), the emotional state can bias the choice. This could be implemented in:  
\- \`systems/turn\_processor.py\` (combat actions)  
\- \`yggdrasil/ravens/huginn.py\` (when retrieving relevant NPC memories, include emotional context)  
\- Or simply feed the emotional state into the prompt and let the AI decide (simplest).

We'll start with the prompt-only approach (Phase 3\) and later add explicit behavioral sampling for more deterministic NPC reactions.

\#\#\#\# \*\*4.3 Player Character Automation\*\*  
If the player wants the AI to control their character (e.g., for downtime), the emotional state can influence their actions. This can be toggled via a config flag.

\---

\#\#\# \*\*Phase 5: Integration with Existing Systems\*\*    
\*\*Goal\*\*: Connect emotional engine with fear, chronotype, stress, rituals.

\#\#\#\# \*\*5.1 Fear System\*\*  
The design mentions "Fear System" feeding \`Hugr-Tíð\` temporarily. In the current architecture, there is a \`fear\_factor\` in state\_modifiers. We can treat \`fear\_factor\` as the global "ambient fear" (e.g., from environment), while emotional fear is per character.

In \`\_update\_emotional\_states\`, after computing emotional fear, we can add a portion of it to the global \`fear\_factor\` (or to a separate \`player\_fear\`). Conversely, high global fear should amplify emotional fear stimuli (multiplicative). We'll define a bidirectional relationship.

\#\#\#\# \*\*5.2 Chronotype\*\*  
Chronotype affects emotional processing: nocturnal characters process emotions more cleanly at night. We already have \`chronotype\` in character profiles and \`time\_of\_day\` in GameState.

Modify \`EmotionalEngine.compute\_impact\` to include a chronotype modifier:

\`\`\`python  
def chronotype\_modifier(self, time\_of\_day, chronotype):  
    if chronotype \== 'nocturnal' and (time\_of\_day in \['night', 'midnight'\]):  
        return 1.1  \# cleaner processing? Or lower impact?  
    elif chronotype \== 'diurnal' and (time\_of\_day in \['morning', 'midday'\]):  
        return 1.1  
    else:  
        return 0.9  \# misalignment increases emotional difficulty  
\`\`\`

\#\#\#\# \*\*5.3 Stress System\*\*  
The design says "Internalized emotions feed stress accumulation". Add a \`stress\_level\` field to GameState (0-100). Each turn, sum internalized emotions contributions (from \`internalize()\`). When stress exceeds thresholds, trigger events (e.g., panic, rituals). Rituals can reduce stress and regulate emotions.

We can create a new module \`systems/stress\_system.py\` to handle stress mechanics, possibly integrating with the existing chaos system.

\#\#\#\# \*\*5.4 Rituals\*\*  
Rituals (fire, darkness, group rituals) modify emotional states. When a ritual is performed (e.g., via player command or AI narration), we apply modifiers to emotional channels (e.g., reduce anger, reduce rumination). This can be implemented in \`engine.py\` when processing ritual commands.

\---

\#\#\# \*\*Phase 6: Testing & Tuning\*\*    
\*\*Goal\*\*: Validate that the system produces believable, non-stereotypical behavior.

\#\#\#\# \*\*6.1 Create Test Characters\*\*  
Generate a set of test characters with varied tf\_axis, gender\_axis, and individual offsets. Run through scenarios and log emotional progression.

\#\#\#\# \*\*6.2 Add Debug Commands\*\*  
Add slash commands to inspect emotional state: \`/emotions\`, \`/stress\`, etc.

\#\#\#\# \*\*6.3 Tune Parameters\*\*  
Adjust decay rates, expression thresholds, and keyword intensities based on playtesting.

\---

\#\# \*\*Recommended Code Changes (Detailed)\*\*

\#\#\# \*\*File: \`data/character\_schema.yaml\` (or similar)\*\*  
Add the emotion\_profile section with default values.

\#\#\# \*\*File: \`systems/emotional\_engine.py\` (new)\*\*  
Implement \`EmotionalEngine\` class as described.

\#\#\# \*\*File: \`engine.py\`\*\*  
Add imports and new methods:

\`\`\`python  
from systems.emotional\_engine import EmotionalEngine, EmotionalState

class NorseSagaEngine:  
    def \_\_init\_\_(self, ...):  
        \# ... existing ...  
        self.emotional\_engine \= None  \# will be initialized per character  
        self.stress\_level \= 0

    def \_extract\_emotional\_stimuli(self, text: str) \-\> Dict\[str, float\]:  
        """Simple keyword-based emotion extraction."""  
        stimuli \= defaultdict(float)  
        words \= text.lower().split()  
        for word in words:  
            for emotion, keywords in EMOTION\_KEYWORDS.items():  
                if word in keywords:  
                    stimuli\[emotion\] \+= 0.1  \# base strength  
        return dict(stimuli)

    def \_update\_emotional\_states(self, stimuli: Dict\[str, float\]):  
        \# Player  
        player\_profile \= self.state.player\_character.get('emotion\_profile', DEFAULT\_EMOTION\_PROFILE)  
        player\_engine \= EmotionalEngine(player\_profile)  
        for ch, strength in stimuli.items():  
            impact \= player\_engine.compute\_impact('narrative', strength, ch)  
            player\_engine.update\_state(ch, impact, self.state.turn\_count)  
            if not player\_engine.should\_express(ch):  
                self.stress\_level \+= player\_engine.internalize(ch)  
        self.state.player\_emotional\_state \= player\_engine.state

        \# NPCs  
        for npc in self.state.npcs\_present:  
            npc\_id \= npc\['id'\]  
            npc\_profile \= npc.get('emotion\_profile', DEFAULT\_EMOTION\_PROFILE)  
            npc\_engine \= EmotionalEngine(npc\_profile)  
            \# Use same stimuli? Or maybe extract NPC-specific stimuli from narrative  
            \# For simplicity, reuse global stimuli  
            for ch, strength in stimuli.items():  
                impact \= npc\_engine.compute\_impact('narrative', strength, ch)  
                npc\_engine.update\_state(ch, impact, self.state.turn\_count)  
            self.state.npc\_emotional\_states\[npc\_id\] \= npc\_engine.state

    def \_decay\_emotional\_states(self):  
        \# Decay all states by 1 turn  
        for state in \[self.state.player\_emotional\_state\] \+ list(self.state.npc\_emotional\_states.values()):  
            for ch in state.\_\_dict\_\_:  
                setattr(state, ch, max(0, getattr(state, ch) \- 0.05))  \# simple decay  
\`\`\`

Call \`\_update\_emotional\_states\` after AI response, and \`\_decay\_emotional\_states\` at the beginning of each turn.

\#\#\# \*\*File: \`prompt\_builder.py\`\*\*  
Add method to format emotional state:

\`\`\`python  
def build\_emotional\_context(self, game\_state):  
    lines \= \["=== EMOTIONAL STATE \==="\]  
    \# Player  
    ps \= game\_state.player\_emotional\_state  
    lines.append(f"Player: fear {ps.fear:.1f}, anger {ps.anger:.1f}, joy {ps.joy:.1f}, sadness {ps.sadness:.1f}, shame {ps.shame:.1f}, attachment {ps.attachment:.1f}")  
    \# NPCs present  
    for npc in game\_state.npcs\_present:  
        nid \= npc\['id'\]  
        if nid in game\_state.npc\_emotional\_states:  
            es \= game\_state.npc\_emotional\_states\[nid\]  
            lines.append(f"{npc\['name'\]}: fear {es.fear:.1f}, anger {es.anger:.1f}, joy {es.joy:.1f}")  
    return "\\n".join(lines)  
\`\`\`

Insert this into the prompt layers.

\#\#\# \*\*File: \`systems/\_\_init\_\_.py\`\*\*  
Expose EmotionalEngine.

\#\#\# \*\*File: \`session/session\_manager.py\`\*\*  
Add emotional state to saved session data.

\#\#\# \*\*File: \`config.yaml\`\*\*  
Add optional tuning parameters: \`emotion\_decay\_rate\`, \`stress\_thresholds\`, etc.

\---

\#\# \*\*Future Enhancements\*\*

\- \*\*AI-driven emotion extraction\*\*: Use a small LLM call (via Yggdrasil) to analyze narrative for emotional content and assign intensities.  
\- \*\*Emotional contagion\*\*: NPCs influencing each other's emotions.  
\- \*\*Long-term emotional memory\*\*: Characters remember past emotional events (integrate with MemorySystemV3).  
\- \*\*Trauma and emotional imprinting\*\*: As mentioned in the design doc.

\---

\#\# \*\*Conclusion\*\*

This staged plan integrates a sophisticated emotional system into the Norse Saga Engine while respecting its existing architecture. The emotional engine is modular, tunable, and avoids stereotypes by using continuous axes and individual variance. By implementing in phases, we ensure stability and allow for iterative testing.

\*\*Next Steps\*\*: Begin with Phase 1 (data structures) and Phase 2 (core engine) as they form the foundation. Then proceed to prompt integration and behavioral mapping. The integration with existing systems can be done in parallel once the core is stable.