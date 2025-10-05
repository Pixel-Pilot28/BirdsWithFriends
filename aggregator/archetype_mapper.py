"""
Character archetype mapping system.

Maps bird species to personality archetypes for storytelling.
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ArchetypeMapper:
    """Maps bird species to character archetypes."""
    
    def __init__(self, mapping_file: str = None):
        """
        Initialize the archetype mapper.
        
        Args:
            mapping_file: Path to archetype mapping file (JSON or YAML)
        """
        self.mapping_file = mapping_file or "data/archetype_mapping.yaml"
        self.species_archetypes = {}
        self.archetype_descriptions = {}
        
        # Load mapping from file
        self._load_mapping()
    
    def _load_mapping(self):
        """Load archetype mapping from file."""
        try:
            mapping_path = Path(self.mapping_file)
            
            if not mapping_path.exists():
                logger.warning(f"Mapping file {self.mapping_file} not found, using defaults")
                self._create_default_mapping()
                return
            
            with open(mapping_path, 'r', encoding='utf-8') as f:
                if mapping_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.species_archetypes = data.get('species_archetypes', {})
            self.archetype_descriptions = data.get('archetype_descriptions', {})
            
            logger.info(f"Loaded {len(self.species_archetypes)} species mappings")
            
        except Exception as e:
            logger.error(f"Failed to load mapping file: {e}")
            self._create_default_mapping()
    
    def _create_default_mapping(self):
        """Create default archetype mapping."""
        self.species_archetypes = {
            # Cardinals and allies - Bold personalities
            "Northern Cardinal": "bold gossip",
            "Pyrrhuloxia": "desert sage",
            
            # Jays and crows - Intelligent troublemakers
            "Blue Jay": "clever troublemaker",
            "Steller's Jay": "mountain trickster",
            "American Crow": "wise observer", 
            "Common Grackle": "street-smart survivor",
            
            # Robins and thrushes - Friendly neighbors
            "American Robin": "cheerful neighbor",
            "Eastern Bluebird": "gentle optimist",
            "Wood Thrush": "forest philosopher",
            
            # Sparrows - Humble workers
            "House Sparrow": "busy worker",
            "White-throated Sparrow": "quiet musician",
            "Song Sparrow": "local storyteller",
            
            # Finches - Social butterflies
            "American Goldfinch": "sunny socialite", 
            "House Finch": "friendly chatterbox",
            "Purple Finch": "sophisticated visitor",
            
            # Woodpeckers - Industrious builders
            "Downy Woodpecker": "persistent craftsman",
            "Red-bellied Woodpecker": "energetic builder",
            "Pileated Woodpecker": "master carpenter",
            
            # Blackbirds - Dramatic performers
            "Red-winged Blackbird": "territorial performer",
            "European Starling": "versatile mimic",
            "Brown-headed Cowbird": "mysterious wanderer",
            
            # Doves and pigeons - Peaceful mediators
            "Mourning Dove": "gentle peacekeeper",
            "Rock Pigeon": "urban survivor",
            "Eurasian Collared-Dove": "polite newcomer",
            
            # Chickadees and nuthatches - Acrobatic entertainers
            "Black-capped Chickadee": "acrobatic entertainer",
            "White-breasted Nuthatch": "upside-down comedian",
            "Tufted Titmouse": "curious explorer",
            
            # Warblers - Energetic travelers
            "Yellow Warbler": "energetic traveler",
            "American Redstart": "flashy dancer",
            "Common Yellowthroat": "secretive spy",
        }
        
        self.archetype_descriptions = {
            "bold gossip": "Confident and social, always ready with the latest news from around the neighborhood.",
            "desert sage": "Wise and adapted, sharing ancient knowledge of survival in harsh lands.",
            "clever troublemaker": "Intelligent and mischievous, always finding creative solutions (and problems).",
            "mountain trickster": "Playful and resourceful, using wit and cunning in high places.",
            "wise observer": "Thoughtful and perceptive, watching the world with knowing eyes.",
            "street-smart survivor": "Adaptable and tough, thriving in urban environments.",
            "cheerful neighbor": "Friendly and reliable, the first to greet you in the morning.",
            "gentle optimist": "Soft-spoken and hopeful, always seeing the bright side.",
            "forest philosopher": "Contemplative and deep, pondering life's mysteries among the trees.",
            "busy worker": "Industrious and practical, always building or gathering.",
            "quiet musician": "Talented and modest, sharing beautiful songs when the mood strikes.",
            "local storyteller": "Knowledgeable and engaging, full of tales about the area.",
            "sunny socialite": "Bright and gregarious, bringing joy to every gathering.",
            "friendly chatterbox": "Talkative and warm, never meeting a stranger.",
            "sophisticated visitor": "Refined and cultured, gracing us with their presence.",
            "persistent craftsman": "Skilled and determined, perfecting their art through repetition.",
            "energetic builder": "Dynamic and creative, always working on the next project.",
            "master carpenter": "Expert and powerful, creating impressive architectural works.",
            "territorial performer": "Bold and dramatic, defending their stage with passion.",
            "versatile mimic": "Talented and adaptable, learning new tricks constantly.",
            "mysterious wanderer": "Enigmatic and unpredictable, following their own path.",
            "gentle peacekeeper": "Calm and soothing, bringing tranquility to tense situations.",
            "urban survivor": "Hardy and practical, making the best of city life.",
            "polite newcomer": "Courteous and well-mannered, fitting in while maintaining their identity.",
            "acrobatic entertainer": "Playful and athletic, delighting audiences with their antics.",
            "upside-down comedian": "Quirky and amusing, finding humor in unique perspectives.",
            "curious explorer": "Inquisitive and adventurous, always investigating something new.",
            "energetic traveler": "Restless and vibrant, bringing stories from distant places.",
            "flashy dancer": "Graceful and showy, expressing themselves through movement.",
            "secretive spy": "Elusive and observant, gathering intelligence from the shadows."
        }
    
    def get_archetype(self, species: str) -> Optional[str]:
        """
        Get archetype for a species.
        
        Args:
            species: Species name (e.g., "Northern Cardinal")
            
        Returns:
            Archetype string or None if not mapped
        """
        return self.species_archetypes.get(species)
    
    def get_archetype_description(self, archetype: str) -> Optional[str]:
        """
        Get description for an archetype.
        
        Args:
            archetype: Archetype name
            
        Returns:
            Description string or None if not found
        """
        return self.archetype_descriptions.get(archetype)
    
    def get_all_archetypes(self) -> List[str]:
        """Get list of all available archetypes."""
        return list(self.archetype_descriptions.keys())
    
    def get_species_for_archetype(self, archetype: str) -> List[str]:
        """
        Get all species that map to a given archetype.
        
        Args:
            archetype: Archetype name
            
        Returns:
            List of species names
        """
        return [
            species for species, arch in self.species_archetypes.items()
            if arch == archetype
        ]
    
    def add_species_mapping(self, species: str, archetype: str):
        """
        Add or update a species-to-archetype mapping.
        
        Args:
            species: Species name
            archetype: Archetype name
        """
        self.species_archetypes[species] = archetype
    
    def save_mapping(self, output_file: str = None):
        """
        Save current mapping to file.
        
        Args:
            output_file: Output file path (defaults to original mapping file)
        """
        output_path = Path(output_file or self.mapping_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "species_archetypes": self.species_archetypes,
            "archetype_descriptions": self.archetype_descriptions
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if output_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=True)
                else:
                    json.dump(data, f, indent=2, sort_keys=True)
            
            logger.info(f"Saved mapping to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save mapping: {e}")


# Global archetype mapper instance
archetype_mapper = ArchetypeMapper()