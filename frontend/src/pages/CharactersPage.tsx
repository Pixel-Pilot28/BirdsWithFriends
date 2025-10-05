import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Users, Edit3, Trash2, Merge, Clock, Eye } from 'lucide-react';
import { ApiService } from '@/services/api';
import { Character, CharacterUpdateForm } from '@/types/api';
import { formatDistanceToNow } from 'date-fns';
import LoadingSpinner from '@/components/LoadingSpinner';

interface CharacterEditModalProps {
  character: Character | null;
  isOpen: boolean;
  onClose: () => void;
}

function CharacterEditModal({ character, isOpen, onClose }: CharacterEditModalProps) {
  const [name, setName] = useState(character?.name || '');
  const [archetype, setArchetype] = useState(character?.archetype || '');
  const queryClient = useQueryClient();

  const updateMutation = useMutation(
    (updates: CharacterUpdateForm) => 
      character ? ApiService.updateCharacter(character.id, updates) : Promise.reject(),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('characters');
        onClose();
      },
    }
  );

  const deleteMutation = useMutation(
    () => character ? ApiService.deleteCharacter(character.id) : Promise.reject(),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('characters');
        onClose();
      },
    }
  );

  if (!isOpen || !character) return null;

  const handleSave = () => {
    const updates: CharacterUpdateForm = {};
    if (name !== character.name) updates.name = name || undefined;
    if (archetype !== character.archetype) updates.archetype = archetype;
    
    if (Object.keys(updates).length > 0) {
      updateMutation.mutate(updates);
    } else {
      onClose();
    }
  };

  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete ${character.name || character.species}? This action cannot be undone.`)) {
      deleteMutation.mutate();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div className="p-6 border-b">
          <h2 className="text-xl font-display font-semibold text-gray-900">
            Edit Character
          </h2>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="form-label">Species</label>
            <input
              type="text"
              value={character.species}
              disabled
              className="form-input bg-gray-50 text-gray-500"
            />
            <p className="text-xs text-gray-500 mt-1">Species cannot be changed</p>
          </div>

          <div>
            <label className="form-label">Custom Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="form-input"
              placeholder="Give this bird a name..."
            />
          </div>

          <div>
            <label className="form-label">Archetype</label>
            <select
              value={archetype}
              onChange={(e) => setArchetype(e.target.value)}
              className="form-input"
            >
              <option value="Leader">Leader</option>
              <option value="Scout">Scout</option>
              <option value="Guardian">Guardian</option>
              <option value="Follower">Follower</option>
              <option value="Wise Elder">Wise Elder</option>
              <option value="Trickster">Trickster</option>
              <option value="Newcomer">Newcomer</option>
              <option value="Visitor">Visitor</option>
            </select>
          </div>

          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-sm text-gray-600 space-y-1">
              <div><span className="font-medium">First seen:</span> {formatDistanceToNow(new Date(character.first_seen), { addSuffix: true })}</div>
              <div><span className="font-medium">Last seen:</span> {formatDistanceToNow(new Date(character.last_seen), { addSuffix: true })}</div>
              <div><span className="font-medium">Appearances:</span> {character.appearance_count}</div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <button
            onClick={handleDelete}
            disabled={deleteMutation.isLoading}
            className="btn-danger flex items-center space-x-2"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete</span>
          </button>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={updateMutation.isLoading}
              className="btn-primary flex items-center space-x-2"
            >
              {updateMutation.isLoading && <LoadingSpinner size="sm" />}
              <span>Save Changes</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CharactersPage() {
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('active');
  const queryClient = useQueryClient();

  // Fetch characters
  const { data: characters, isLoading, isError } = useQuery<Character[]>(
    ['characters', filter],
    () => ApiService.getCharacters({
      active_only: filter === 'active',
      limit: 100,
    }),
    {
      refetchInterval: 60000, // Refresh every minute
      retry: false,
      refetchOnWindowFocus: false,
    }
  );

  // Merge characters mutation
  const mergeMutation = useMutation(
    ({ sourceId, targetId }: { sourceId: string; targetId: string }) =>
      ApiService.mergeCharacters(sourceId, targetId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('characters');
        setSelectedCharacters([]);
      },
    }
  );

  const handleCharacterSelect = (characterId: string) => {
    setSelectedCharacters(prev => 
      prev.includes(characterId) 
        ? prev.filter(id => id !== characterId)
        : [...prev, characterId]
    );
  };

  const handleMergeSelected = () => {
    if (selectedCharacters.length === 2) {
      const [sourceId, targetId] = selectedCharacters;
      if (window.confirm('Merge the first selected character into the second? This cannot be undone.')) {
        mergeMutation.mutate({ sourceId, targetId });
      }
    }
  };

  const getArchetypeColor = (archetype: string) => {
    const colors: Record<string, string> = {
      'Leader': 'bg-purple-100 text-purple-800',
      'Scout': 'bg-blue-100 text-blue-800',
      'Guardian': 'bg-green-100 text-green-800',
      'Follower': 'bg-gray-100 text-gray-800',
      'Wise Elder': 'bg-yellow-100 text-yellow-800',
      'Trickster': 'bg-orange-100 text-orange-800',
      'Newcomer': 'bg-pink-100 text-pink-800',
      'Visitor': 'bg-indigo-100 text-indigo-800',
    };
    return colors[archetype] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900">Characters</h1>
          <p className="text-gray-600 mt-1">Manage your bird character profiles</p>
        </div>
        
        <div className="card p-12 text-center">
          <Users className="w-16 h-16 mx-auto mb-4 text-yellow-500 opacity-50" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Character service temporarily unavailable
          </h3>
          <p className="text-gray-600 mb-4">
            The backend service is starting up. Character profiles will appear when the service is running.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="btn-secondary"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900">Characters</h1>
          <p className="text-gray-600 mt-1">
            Manage bird characters and their personalities
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-3">
          {selectedCharacters.length === 2 && (
            <button
              onClick={handleMergeSelected}
              disabled={mergeMutation.isLoading}
              className="btn bg-orange-600 text-white hover:bg-orange-700 flex items-center space-x-2"
            >
              <Merge className="w-4 h-4" />
              <span>Merge Selected</span>
            </button>
          )}
          
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as 'all' | 'active' | 'inactive')}
            className="form-input w-auto"
          >
            <option value="active">Active Characters</option>
            <option value="all">All Characters</option>
            <option value="inactive">Inactive Characters</option>
          </select>
        </div>
      </div>

      {/* Selection Info */}
      {selectedCharacters.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="text-blue-800">
              {selectedCharacters.length} character{selectedCharacters.length > 1 ? 's' : ''} selected
              {selectedCharacters.length === 2 && ' - Ready to merge'}
            </div>
            <button
              onClick={() => setSelectedCharacters([])}
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Clear selection
            </button>
          </div>
        </div>
      )}

      {/* Characters Grid */}
      {characters && characters.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {characters.map((character) => (
            <div
              key={character.id}
              className={`card p-6 cursor-pointer transition-all ${
                selectedCharacters.includes(character.id)
                  ? 'ring-2 ring-primary-500 bg-primary-50'
                  : 'hover:shadow-md'
              }`}
              onClick={() => handleCharacterSelect(character.id)}
            >
              {/* Character Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {character.name || `${character.species} #${character.id.slice(-4)}`}
                  </h3>
                  <p className="text-gray-600 text-sm">{character.species}</p>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectedCharacters.includes(character.id)}
                    onChange={() => handleCharacterSelect(character.id)}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                </div>
              </div>

              {/* Archetype Badge */}
              <div className="mb-4">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getArchetypeColor(character.archetype)}`}>
                  {character.archetype}
                </span>
              </div>

              {/* Stats */}
              <div className="space-y-2 text-sm text-gray-600 mb-4">
                <div className="flex items-center space-x-2">
                  <Eye className="w-4 h-4" />
                  <span>{character.appearance_count} appearance{character.appearance_count !== 1 ? 's' : ''}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4" />
                  <span>Last seen {formatDistanceToNow(new Date(character.last_seen), { addSuffix: true })}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingCharacter(character);
                  }}
                  className="btn-secondary text-sm flex items-center space-x-1"
                >
                  <Edit3 className="w-3 h-3" />
                  <span>Edit</span>
                </button>
              </div>

              {/* Notes (if any) */}
              {character.notes && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-xs text-gray-500">{character.notes}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No characters found</h3>
          <p className="text-gray-600">
            Characters will appear here as birds are detected in the live stream.
          </p>
        </div>
      )}

      {/* Character Edit Modal */}
      <CharacterEditModal
        character={editingCharacter}
        isOpen={!!editingCharacter}
        onClose={() => setEditingCharacter(null)}
      />
    </div>
  );
}