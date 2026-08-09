'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { 
  UserPlus, 
  Users, 
  Check, 
  Clock, 
  Search, 
  ShieldCheck, 
  Sparkles,
  MessageSquare,
  Loader2,
  X,
  UserX,
  Ban,
  UserCheck
} from 'lucide-react';

interface FriendsManagerProps {
  onStartDirectMessage?: (peerId: string, peerName: string) => void;
}

export default function FriendsManager({ onStartDirectMessage }: FriendsManagerProps) {
  const queryClient = useQueryClient();
  const [targetInput, setTargetInput] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  const { data: friends, isLoading } = useQuery({
    queryKey: ['connect_friends'],
    queryFn: async () => {
      const res = await apiClient.get('/connect/friends');
      return res.data || [];
    },
  });

  const { data: recommendations } = useQuery({
    queryKey: ['partner_recommendations'],
    queryFn: async () => {
      const res = await apiClient.get('/connect/recommendations');
      return res.data || [];
    },
  });

  const sendRequestMutation = useMutation({
    mutationFn: async (input: string) => {
      const res = await apiClient.post(`/connect/friends/request?target_username_or_id=${encodeURIComponent(input)}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_friends'] });
      queryClient.invalidateQueries({ queryKey: ['partner_recommendations'] });
      setTargetInput('');
      setStatusMsg('Friend request sent! 🚀');
      setTimeout(() => setStatusMsg(''), 3000);
    },
    onError: (err: any) => {
      setStatusMsg(err.response?.data?.detail || 'Failed to send request.');
    },
  });

  const acceptMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.patch(`/connect/friends/${id}/accept`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_friends'] });
      queryClient.invalidateQueries({ queryKey: ['partner_recommendations'] });
    },
  });

  const declineMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.post(`/connect/friends/${id}/reject`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_friends'] });
      queryClient.invalidateQueries({ queryKey: ['partner_recommendations'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/connect/friends/${id}/remove`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_friends'] });
      queryClient.invalidateQueries({ queryKey: ['partner_recommendations'] });
    },
  });

  const blockMutation = useMutation({
    mutationFn: async (userId: string) => {
      await apiClient.post(`/connect/friends/${userId}/block`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connect_friends'] });
      queryClient.invalidateQueries({ queryKey: ['partner_recommendations'] });
      setStatusMsg('User blocked.');
      setTimeout(() => setStatusMsg(''), 3000);
    },
  });

  const activeConnections = friends?.filter((f: any) => f.status === 'accepted') || [];
  const pendingReceived = friends?.filter((f: any) => f.status === 'pending') || [];

  return (
    <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-6 space-y-6 shadow-xl">
      <div className="flex items-center justify-between border-b border-[var(--border-default)] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" /> Connections & Peer Network
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">Search classmates by username, full name, or course department.</p>
        </div>
      </div>

      {/* Add Friend Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (targetInput.trim()) sendRequestMutation.mutate(targetInput.trim());
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          value={targetInput}
          onChange={(e) => setTargetInput(e.target.value)}
          placeholder="Search classmate by username, name, college, or course..."
          className="flex-1 bg-[var(--surface-2)] border border-[var(--border-default)] rounded-2xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={sendRequestMutation.isPending || !targetInput.trim()}
          className="px-5 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg disabled:opacity-50"
        >
          {sendRequestMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />} Add Friend
        </button>
      </form>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs">
          {statusMsg}
        </div>
      )}

      {/* Pending Incoming Friend Requests */}
      {pendingReceived.length > 0 && (
        <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" /> Incoming Friend Requests ({pendingReceived.length})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {pendingReceived.map((f: any) => (
              <div key={f.id} className="p-3 rounded-xl bg-[var(--surface-2)] border border-indigo-500/30 flex items-center justify-between text-xs">
                <div className="font-bold text-white">{f.requester_name || f.addressee_name}</div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => acceptMutation.mutate(f.id)}
                    className="px-3 py-1 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" /> Accept
                  </button>
                  <button
                    onClick={() => declineMutation.mutate(f.id)}
                    className="px-3 py-1 rounded-xl bg-white/10 hover:bg-rose-500/20 text-gray-300 hover:text-rose-300 font-bold text-[11px]"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Connection Lists */}
      {isLoading ? (
        <div className="text-center text-xs text-gray-500 py-6">Loading connection network...</div>
      ) : (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
            Active Connections ({activeConnections.length}):
          </h3>

          {activeConnections.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {activeConnections.map((f: any) => (
                <div
                  key={f.id}
                  className="p-3.5 rounded-2xl bg-[var(--surface-2)] border border-white/5 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-white shrink-0">
                      {f.addressee_name?.charAt(0) || 'P'}
                    </div>
                    <div>
                      <h4 className="font-bold text-white">{f.addressee_name}</h4>
                      <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                        ● Online in ScholarOS
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => onStartDirectMessage && onStartDirectMessage(f.addressee_id || f.requester_id, f.addressee_name || f.requester_name)}
                      className="px-2.5 py-1 rounded-xl bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-500/30 text-[11px] font-bold flex items-center gap-1 transition"
                    >
                      <MessageSquare className="w-3 h-3 text-purple-400" /> Fast DM
                    </button>
                    <button
                      onClick={() => removeMutation.mutate(f.id)}
                      className="p-1.5 rounded-xl text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                      title="Remove Connection"
                    >
                      <UserX className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Dedicated Encouraging Empty State */
            <div className="p-8 text-center rounded-3xl bg-[var(--surface-2)] border border-dashed border-white/10 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mx-auto">
                <Users className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-white">Build Your Study Network</h3>
                <p className="text-xs text-gray-400 max-w-sm mx-auto">
                  Connect with verified classmates to exchange notes, work on assignments, and study together in group rooms.
                </p>
              </div>
              <div className="flex items-center justify-center gap-3 pt-1">
                <button
                  onClick={() => {
                    const el = document.querySelector('input[type="text"]') as HTMLInputElement;
                    if (el) el.focus();
                  }}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md inline-flex items-center gap-1.5"
                >
                  <UserPlus className="w-3.5 h-3.5" /> + Add Friend
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Contextual Suggested Study Partners */}
      <div className="pt-4 border-t border-[var(--border-default)] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" /> Suggested Study Partners ({recommendations?.length || 0})
            </h3>
            <p className="text-[11px] text-gray-400">Classmates matched by institution, specialization, and shared subjects</p>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
            ● Authentic Classmates Only
          </span>
        </div>

        {recommendations && recommendations.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {recommendations
              .filter((rec: any) => {
                if (!targetInput.trim()) return true;
                const query = targetInput.toLowerCase();
                return (
                  rec.full_name?.toLowerCase().includes(query) ||
                  rec.institution_name?.toLowerCase().includes(query) ||
                  rec.field?.toLowerCase().includes(query) ||
                  rec.specialization?.toLowerCase().includes(query)
                );
              })
              .map((rec: any) => (
                <div
                  key={rec.user_id}
                  className="p-4 rounded-2xl bg-[var(--surface-2)] border border-purple-500/20 hover:border-purple-500/50 transition flex flex-col justify-between space-y-3 text-xs shadow-lg group"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-pink-500 flex items-center justify-center font-black text-white shrink-0 shadow-md text-sm">
                        {rec.full_name?.charAt(0) || 'U'}
                      </div>
                      <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        {Math.round(rec.matching_score * 100)}% Match
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-white text-sm group-hover:text-purple-300 transition-colors truncate">
                        {rec.full_name}
                      </h4>
                      <p className="text-[11px] text-indigo-300 font-semibold truncate">
                        {rec.specialization || rec.field || 'Student'}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate">
                        {rec.institution_name || 'ScholarOS Academic Network'}
                      </p>
                    </div>

                    {/* Contextual ML Match Explanation Badge */}
                    <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-[10px] text-purple-200">
                      🤖 <span className="font-semibold text-purple-300">ML Partner Match:</span> {rec.match_reason || `Matched with ${rec.full_name} (${Math.round(rec.matching_score * 100)}%)`}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                    <button
                      onClick={() => onStartDirectMessage && onStartDirectMessage(rec.user_id, rec.full_name)}
                      className="flex-1 py-2 rounded-xl bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 text-[11px] font-bold flex items-center justify-center gap-1.5 transition shadow-sm"
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-purple-400" /> Fast DM
                    </button>
                    {rec.connection_status === 'accepted' ? (
                      <span className="px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-bold text-[11px]">
                        Connected
                      </span>
                    ) : rec.connection_status === 'pending' ? (
                      <span className="px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 font-bold text-[11px]">
                        Pending
                      </span>
                    ) : (
                      <button
                        onClick={() => sendRequestMutation.mutate(rec.user_id)}
                        disabled={sendRequestMutation.isPending}
                        className="px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-[11px] flex items-center gap-1 transition shadow-md disabled:opacity-50"
                      >
                        <UserPlus className="w-3.5 h-3.5" /> Connect
                      </button>
                    )}
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="p-8 text-center rounded-2xl bg-[var(--surface-2)] border border-dashed border-white/10 space-y-2">
            <Users className="w-8 h-8 text-purple-400 mx-auto opacity-80" />
            <p className="text-xs text-gray-300 font-semibold">No other registered peers found in network yet.</p>
            <p className="text-[11px] text-gray-400">Invite classmates or tell friends to register on ScholarOS!</p>
          </div>
        )}
      </div>
    </div>
  );
}
