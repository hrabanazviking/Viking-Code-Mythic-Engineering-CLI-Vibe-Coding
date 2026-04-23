import logging
import numpy as np

logger = logging.getLogger(__name__)

# Elder Futhark rune emotion centroids
EMOTION_CENTROIDS = {
    "Fehu": [0.9, 0.2, 0.1],  # Dominance/excitement
    "Thurisaz": [0.1, 0.9, 0.3],  # Anger/frustration
    "Ansuz": [0.7, 0.5, 0.6],  # Wisdom/insight
    "Raidho": [0.4, 0.3, 0.8],  # Journey/movement
    "Gebo": [0.8, 0.4, 0.5],  # Partnership/gift
    "Wunjo": [0.9, 0.7, 0.4],  # Joy/bliss
    "Hagalaz": [0.2, 0.8, 0.1],  # Disruption/chaos
    "Nauthiz": [0.3, 0.6, 0.2],  # Constraint/need
    "Isa": [0.1, 0.1, 0.1],  # Stillness/ice
    "Jera": [0.5, 0.4, 0.6],  # Harvest/cycle
    "Eihwaz": [0.4, 0.5, 0.7],  # Endurance/protection
    "Perthro": [0.6, 0.3, 0.4],  # Mystery/fate
    "Algiz": [0.7, 0.2, 0.9],  # Protection/awakening
    "Sowilo": [0.9, 0.8, 0.7],  # Success/vitality
    "Tiwaz": [0.8, 0.6, 0.9],  # Justice/leadership
    "Berkana": [0.5, 0.7, 0.3],  # Growth/nurturing
    "Ehwaz": [0.6, 0.5, 0.7],  # Partnership/trust
    "Mannaz": [0.7, 0.6, 0.5],  # Humanity/self
    "Laguz": [0.3, 0.4, 0.8],  # Intuition/flow
    "Ingwaz": [0.4, 0.3, 0.6],  # Potential/gestation
    "Dagaz": [0.8, 0.7, 0.9],  # Breakthrough/awakening
    "Othala": [0.6, 0.5, 0.4]   # Heritage/inheritance
}

def tag_emotion_state(emotion_vector: np.ndarray) -> str:
    """
    Tag an emotion vector with Elder Futhark rune based on closest centroid
    
    Args:
        emotion_vector: [valence, arousal, dominance] normalized 0-1
        
    Returns:
        Closest matching rune name
    """
    # Callers may pass a plain list; convert to ndarray for arithmetic.
    emotion_vector = np.asarray(emotion_vector, dtype=float)
    min_distance = float('inf')
    closest_rune = ""

    for rune, centroid in EMOTION_CENTROIDS.items():
        distance = np.linalg.norm(emotion_vector - np.asarray(centroid, dtype=float))
        if distance < min_distance:
            min_distance = distance
            closest_rune = rune
            
    return closest_rune


def add_memory_node(memory_data: dict, emotion_vector: np.ndarray = None):
    """
    Add memory node to Yggdrasil with optional emotion tagging
    
    Args:
        memory_data: Memory content dictionary
        emotion_vector: Optional emotion vector for rune tagging
    """
    if emotion_vector is not None:
        rune_tag = tag_emotion_state(emotion_vector)
        memory_data['emotion_rune'] = rune_tag
    
    # Actual storage implementation would go here
    logger.debug("Storing memory with rune tag: %s", memory_data.get('emotion_rune', 'N/A'))