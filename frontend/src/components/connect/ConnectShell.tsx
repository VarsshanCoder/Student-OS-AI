'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { 
  Globe, 
  Users, 
  MessageSquare, 
  BookOpen,
  Layers, 
  FileText, 
  Sparkles, 
  Plus,
  Loader2,
  X,
  Share2
} from 'lucide-react';
import FriendsManager from './FriendsManager';
import ChatCanvas from './ChatCanvas';
import SharedWhiteboard from './SharedWhiteboard';
import CollabEditor from './CollabEditor';

export default function ConnectShell() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'friends' | 'chat' | 'groups'>('friends');
  const [groupSubTab, setGroupSubTab] = useState<'channels' | 'whiteboard' | 'editor'>('channels');
  const [selectedChannel, setSelectedChannel] = useState<string>('general_study_lounge');

  // Shared Resources Side Panel
  const [showSharedDrawer, setShowSharedDrawer] = useState(false);

  // Create Group Modal
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [groupName, setGroupName] = useState('');
  const [groupDesc, setGroupDesc] = useState('');
  const [groupSubject, setGroupSubject] = useState('');

  const { data: groups } = useQuery({
    queryKey: ['connect_groups'],
    queryFn: async () => {
      const res = await apiClient.get('/connect/groups');
      return res.data || [];
    },
  });

  const { data: sharedResources } = useQuery({
    queryKey: ['shared_resources'],
    queryFn: async () => {
      const res = await apiClient.get('/connect/resources/shared');
      return res.data || [];
    },
  });

  const createGroupMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/connect/groups', {
        name: groupName,
        description: groupDesc,
        subject_name: groupSubject
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_groups'] });
      setShowCreateGroup(false);
      setGroupName('');
      setGroupDesc('');
      setGroupSubject('');
    },
  });

  const handleStartDirectMessage = (peerId: string, peerName: string) => {
    const channelId = `dm_${peerId}`;
    setSelectedChannel(channelId);
    setActiveTab('chat');
  };

  return (
    <div className="space-y-4 sm:space-y-6 max-w-7xl w-full mx-auto pb-24 md:pb-16 overflow-x-hidden">
      {/* Header Banner */}
      <div className="p-4 sm:p-6 md:p-8 rounded-3xl bg-gradient-to-r from-indigo-900/40 via-purple-900/30 to-black border border-indigo-500/30 backdrop-blur-xl shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 w-full">
        <div className="space-y-1.5 w-full md:w-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-[11px] font-bold">
            <Globe className="w-3.5 h-3.5 text-indigo-400" /> ScholarConnect Academic Engine
          </div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-white leading-tight">
            Academic Collaboration & Peer Network
          </h1>
          <p className="text-xs sm:text-sm text-gray-300 max-w-xl leading-relaxed">
            Connect with verified classmates, exchange study notes, collaborate in real-time group workspaces, and study together.
          </p>
        </div>

        <button
          onClick={() => setShowCreateGroup(true)}
          className="w-full sm:w-auto px-5 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 transition"
        >
          <Plus className="w-4 h-4" /> Create Study Group
        </button>
      </div>

      {/* Primary Navigation Bar (3 Primary Modes: Friends, Messages, Study Groups) */}
      <div className="no-scrollbar flex items-center justify-between border-b border-[var(--border-default)] text-xs font-bold w-full pb-1">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[
            { id: 'friends', label: '👥 Friends', icon: Users },
            { id: 'chat', label: '💬 Messages', icon: MessageSquare },
            { id: 'groups', label: '📚 Study Groups', icon: BookOpen }
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`px-4 py-2.5 rounded-2xl font-bold flex items-center gap-2 transition shrink-0 border ${
                activeTab === t.id
                  ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                  : 'bg-[var(--surface-1)] text-gray-400 border-[var(--border-default)] hover:text-white'
              }`}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === 'chat' && (
          <button
            onClick={() => setShowSharedDrawer(!showSharedDrawer)}
            className="px-3.5 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-bold flex items-center gap-1.5 transition"
          >
            <Share2 className="w-3.5 h-3.5 text-purple-400" /> Shared Resources ({sharedResources?.length || 0})
          </button>
        )}
      </div>

      {/* TAB CONTENT RENDERER */}
      <div className="min-h-[450px] w-full">
        {/* Mode 1: Friends Manager */}
        {activeTab === 'friends' && <FriendsManager onStartDirectMessage={handleStartDirectMessage} />}

        {/* Mode 2: 1-on-1 Messages & Channels */}
        {activeTab === 'chat' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-[550px] sm:h-[600px] w-full">
            <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-3 space-y-3 overflow-y-auto max-h-[220px] lg:max-h-full">
              <div className="space-y-1">
                <h3 className="font-bold text-[11px] uppercase tracking-wider text-gray-400 px-2">Academic Conversations</h3>
                <button
                  onClick={() => setSelectedChannel('general_study_lounge')}
                  className={`w-full p-2.5 rounded-2xl text-xs font-bold text-left transition border ${
                    selectedChannel === 'general_study_lounge'
                      ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40'
                      : 'bg-white/5 text-gray-300 border-transparent hover:border-white/10'
                  }`}
                >
                  # general_study_lounge
                </button>

                {(groups || []).map((g: any) => (
                  <button
                    key={g.id}
                    onClick={() => setSelectedChannel(g.id)}
                    className={`w-full p-2.5 rounded-2xl text-xs font-bold text-left transition border ${
                      selectedChannel === g.id
                        ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40'
                        : 'bg-white/5 text-gray-300 border-transparent hover:border-white/10'
                    }`}
                  >
                    # {g.name}
                  </button>
                ))}
              </div>
            </div>

            <div className={`h-full w-full ${showSharedDrawer ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
              <ChatCanvas channelId={selectedChannel} />
            </div>

            {/* Shared Resources Side Drawer */}
            {showSharedDrawer && (
              <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-4 space-y-3 overflow-y-auto h-full">
                <div className="flex items-center justify-between border-b border-white/10 pb-2">
                  <h3 className="font-bold text-xs text-purple-300 flex items-center gap-1.5">
                    <Share2 className="w-3.5 h-3.5 text-purple-400" /> Shared Resources
                  </h3>
                  <button onClick={() => setShowSharedDrawer(false)} className="text-gray-400 hover:text-white text-xs">✕</button>
                </div>

                <div className="space-y-2 text-xs">
                  {sharedResources && sharedResources.length > 0 ? (
                    sharedResources.map((res: any) => (
                      <div key={res.id} className="p-3 rounded-2xl bg-[var(--surface-2)] border border-purple-500/20 space-y-1">
                        <div className="font-bold text-white truncate">{res.resource_title}</div>
                        <div className="text-[10px] text-gray-400 flex items-center justify-between">
                          <span>Owner: {res.owner_name}</span>
                          <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">{res.permission}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-gray-500 text-center py-6">No shared notes or documents in this conversation yet.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Mode 3: Study Groups Workspace */}
        {activeTab === 'groups' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 border-b border-[var(--border-default)] pb-2 text-xs font-bold">
              <button
                onClick={() => setGroupSubTab('channels')}
                className={`px-3.5 py-1.5 rounded-xl transition ${groupSubTab === 'channels' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Group Rooms ({groups?.length || 0})
              </button>
              <button
                onClick={() => setGroupSubTab('whiteboard')}
                className={`px-3.5 py-1.5 rounded-xl transition ${groupSubTab === 'whiteboard' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Interactive Whiteboard
              </button>
              <button
                onClick={() => setGroupSubTab('editor')}
                className={`px-3.5 py-1.5 rounded-xl transition ${groupSubTab === 'editor' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
              >
                Collaborative Notes
              </button>
            </div>

            {groupSubTab === 'channels' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(groups || []).map((g: any) => (
                  <div key={g.id} className="p-4 rounded-3xl bg-[var(--surface-1)] border border-[var(--border-default)] space-y-3 shadow-lg">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-sm text-white">{g.name}</h3>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {g.member_count} members
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 line-clamp-2">{g.description || 'Collaborative study group workspace.'}</p>
                    <button
                      onClick={() => {
                        setSelectedChannel(g.id);
                        setActiveTab('chat');
                      }}
                      className="w-full py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-xs font-bold transition"
                    >
                      Open Study Group Chat
                    </button>
                  </div>
                ))}
              </div>
            )}

            {groupSubTab === 'whiteboard' && <SharedWhiteboard />}
            {groupSubTab === 'editor' && <CollabEditor />}
          </div>
        )}
      </div>

      {/* Create Group Modal */}
      {showCreateGroup && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border-default)] pb-3">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" /> Create Academic Study Group
              </h3>
              <button onClick={() => setShowCreateGroup(false)} className="text-gray-400 hover:text-white font-bold text-xs">
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                createGroupMutation.mutate();
              }}
              className="space-y-3"
            >
              <div>
                <label className="text-xs font-bold text-gray-300 block mb-1">Group Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Advanced Machine Learning Prep"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="w-full bg-[var(--surface-2)] border border-[var(--border-default)] rounded-2xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-300 block mb-1">Subject</label>
                <input
                  type="text"
                  placeholder="e.g. Computer Science"
                  value={groupSubject}
                  onChange={(e) => setGroupSubject(e.target.value)}
                  className="w-full bg-[var(--surface-2)] border border-[var(--border-default)] rounded-2xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-gray-300 block mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Group goals, exam dates, or study schedule..."
                  value={groupDesc}
                  onChange={(e) => setGroupDesc(e.target.value)}
                  className="w-full bg-[var(--surface-2)] border border-[var(--border-default)] rounded-2xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateGroup(false)}
                  className="px-4 py-2 text-xs font-bold text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createGroupMutation.isPending || !groupName.trim()}
                  className="px-5 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 flex items-center gap-1.5"
                >
                  {createGroupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Create Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
