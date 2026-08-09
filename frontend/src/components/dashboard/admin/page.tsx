'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAppStore } from '@/stores/app-store';
import { 
  Shield, 
  Users, 
  FileText, 
  BookOpen, 
  CalendarDays, 
  Trash2, 
  Eye, 
  Search, 
  AlertTriangle, 
  X, 
  Check, 
  Sparkles, 
  Building2, 
  GraduationCap, 
  Clock, 
  ShieldAlert,
  ArrowLeft,
  KeyRound,
  Ban,
  RotateCcw,
  Activity,
  History,
  Lock,
  UserCheck,
  UserX
} from 'lucide-react';
import Link from 'next/link';
import MarkdownRenderer from '@/components/MarkdownRenderer';

interface AdminUserItem {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  role: string;
  is_active: boolean;
  subscription_tier: string;
  onboarding_completed: boolean;
  institution_name?: string;
  education_level?: string;
  notes_count: number;
  pdfs_count: number;
  study_plans_count: number;
  created_at: string;
  last_login_at?: string;
}

interface InspectedUserData {
  user_info: {
    id: string;
    email: string;
    full_name: string;
    is_admin: boolean;
    role: string;
    is_active: boolean;
    subscription_tier: string;
    created_at: string;
    last_login_at?: string;
    onboarding_completed: boolean;
    institution_name?: string;
    education_level?: string;
    field?: string;
    specialization?: string;
    subjects: string[];
    connections_count: number;
  };
  notes: Array<{
    id: string;
    title: string;
    content: string;
    source: string;
    word_count: number;
    created_at: string;
  }>;
  pdfs: Array<{
    id: string;
    filename: string;
    page_count: number;
    file_size: string | number;
    created_at: string;
  }>;
  study_plans: Array<{
    id: string;
    title: string;
    start_date: string;
    end_date: string;
    blocks_count: number;
  }>;
}

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { user } = useAppStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [inspectingUserId, setInspectingUserId] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'overview' | 'academic' | 'activity' | 'resources' | 'connections' | 'sessions' | 'security' | 'audit'>('overview');
  const [viewingNoteContent, setViewingNoteContent] = useState<{ title: string; content: string } | null>(null);

  const [deletingUser, setDeletingUser] = useState<AdminUserItem | null>(null);
  const [suspendingUser, setSuspendingUser] = useState<AdminUserItem | null>(null);
  const [actionError, setActionError] = useState('');

  // Password reset state
  const [resettingUser, setResettingUser] = useState<AdminUserItem | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [resetMsg, setResetMsg] = useState('');
  const [resetError, setResetError] = useState('');

  // Audit Logs view mode
  const [mainView, setMainView] = useState<'users' | 'audit'>('users');

  // 1. Fetch current logged-in user profile to verify admin role
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['user_profile'],
    queryFn: async () => {
      const res = await apiClient.get('/users/me/profile');
      return res.data;
    },
  });

  const isAdmin = Boolean(profile?.is_admin || user?.is_admin || profile?.role === 'SUPER_ADMIN' || user?.email === 'admin2009@gmail.com');

  // 2. Fetch admin overall platform stats
  const { data: stats } = useQuery({
    queryKey: ['admin_stats'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/stats');
      return res.data;
    },
    enabled: isAdmin,
  });

  // 3. Fetch all registered users
  const { data: usersList, isLoading: usersLoading } = useQuery<AdminUserItem[]>({
    queryKey: ['admin_users'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/users');
      return res.data || [];
    },
    enabled: isAdmin,
  });

  // 4. Fetch full inspected data for selected user
  const { data: inspectedData, isLoading: inspectingLoading } = useQuery<InspectedUserData>({
    queryKey: ['inspect_user', inspectingUserId],
    queryFn: async () => {
      const res = await apiClient.get(`/admin/users/${inspectingUserId}/inspect`);
      return res.data;
    },
    enabled: Boolean(isAdmin && inspectingUserId),
  });

  // 5. Fetch platform audit logs
  const { data: auditLogs, isLoading: auditLoading } = useQuery({
    queryKey: ['admin_audit_logs'],
    queryFn: async () => {
      const res = await apiClient.get('/admin/audit-logs');
      return res.data || [];
    },
    enabled: Boolean(isAdmin && mainView === 'audit'),
  });

  // 6. Delete User Mutation
  const deleteUserMutation = useMutation({
    mutationFn: async (userId: string) => {
      const res = await apiClient.delete(`/admin/users/${userId}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin_users'] });
      queryClient.invalidateQueries({ queryKey: ['admin_stats'] });
      setDeletingUser(null);
      setInspectingUserId(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || 'Failed to delete user.');
    },
  });

  // 7. Suspend / Restore User Mutation
  const toggleSuspendMutation = useMutation({
    mutationFn: async ({ userId, suspend }: { userId: string; suspend: boolean }) => {
      const endpoint = suspend ? `/admin/users/${userId}/suspend` : `/admin/users/${userId}/restore`;
      const res = await apiClient.patch(endpoint);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin_users'] });
      setSuspendingUser(null);
    },
    onError: (err: any) => {
      setActionError(err.response?.data?.detail || 'Failed to update account status.');
    },
  });

  // 8. Reset Password Mutation
  const resetPasswordMutation = useMutation({
    mutationFn: async ({ userId, pass }: { userId: string; pass: string }) => {
      const res = await apiClient.post(`/admin/users/${userId}/reset-password`, {
        new_password: pass,
      });
      return res.data;
    },
    onSuccess: (data) => {
      setResetMsg(data.message || 'Password reset successfully!');
      setResetError('');
      setTimeout(() => {
        setResettingUser(null);
        setNewPassword('');
        setResetMsg('');
      }, 2000);
    },
    onError: (err: any) => {
      setResetError(err.response?.data?.detail || 'Failed to reset password.');
    },
  });

  const handleResetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingUser || !newPassword.trim()) return;
    resetPasswordMutation.mutate({ userId: resettingUser.id, pass: newPassword.trim() });
  };

  // Access Control Guard
  if (profileLoading) {
    return <div className="p-12 text-center text-xs text-gray-400">Verifying security credentials...</div>;
  }

  if (!isAdmin) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-rose-950/20 border border-rose-500/30 rounded-3xl p-8 text-center space-y-4 shadow-2xl backdrop-blur-xl">
          <div className="w-16 h-16 rounded-2xl bg-rose-600/20 text-rose-400 border border-rose-500/30 flex items-center justify-center mx-auto">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-black text-white">403 - Access Denied</h1>
          <p className="text-xs text-rose-200/80 leading-relaxed">
            Admin privileges are required to view the ScholarOS Master Control Panel. Please sign in with an authorized admin account.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Filter users by search
  const filteredUsers = usersList?.filter((u) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      u.full_name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      (u.institution_name && u.institution_name.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Admin Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-rose-900/40 via-purple-900/30 to-black border border-rose-500/30 backdrop-blur-xl shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 text-xs font-semibold border border-rose-500/30">
            <Shield className="w-4 h-4 text-rose-400" /> Master Admin Control Center
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white">Platform Administration</h1>
          <p className="text-xs sm:text-sm text-gray-300 max-w-2xl leading-relaxed">
            Logged in as <span className="font-bold text-rose-300">{profile?.email || user?.email}</span> ({profile?.role || 'SUPER_ADMIN'}). Inspect user accounts, manage subscriptions, view audit trails, and enforce security policies.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-black/40 p-1.5 rounded-2xl border border-white/10 shrink-0">
          <button
            onClick={() => setMainView('users')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              mainView === 'users' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" /> User Directory
          </button>
          <button
            onClick={() => setMainView('audit')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              mainView === 'audit' ? 'bg-purple-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'
            }`}
          >
            <History className="w-4 h-4" /> Platform Audit Trail
          </button>
        </div>
      </div>

      {/* Platform Statistics Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-2xl p-5 space-y-1 shadow-lg">
          <div className="flex items-center gap-2 text-indigo-400">
            <Users className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Total Users</span>
          </div>
          <p className="text-2xl font-black text-white">{stats?.total_users || 0}</p>
        </div>

        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-2xl p-5 space-y-1 shadow-lg">
          <div className="flex items-center gap-2 text-purple-400">
            <BookOpen className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Authored Notes</span>
          </div>
          <p className="text-2xl font-black text-white">{stats?.total_notes || 0}</p>
        </div>

        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-2xl p-5 space-y-1 shadow-lg">
          <div className="flex items-center gap-2 text-rose-400">
            <FileText className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Uploaded Documents</span>
          </div>
          <p className="text-2xl font-black text-white">{stats?.total_pdfs || 0}</p>
        </div>

        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-2xl p-5 space-y-1 shadow-lg">
          <div className="flex items-center gap-2 text-emerald-400">
            <CalendarDays className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Active Study Plans</span>
          </div>
          <p className="text-2xl font-black text-white">{stats?.total_study_plans || 0}</p>
        </div>
      </div>

      {mainView === 'users' ? (
        /* User Management Table Section */
        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-6 space-y-6 shadow-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-400" /> Registered Platform Users ({usersList?.length || 0})
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">Manage accounts, inspect detailed user memory, reset passwords, and audit actions.</p>
            </div>

            <div className="flex items-center gap-3 bg-[var(--surface-2)] border border-[var(--border-default)] rounded-xl px-3.5 py-2 w-full sm:w-72">
              <Search className="w-4 h-4 text-gray-400 shrink-0" />
              <input
                type="text"
                placeholder="Search by name, email, or institution..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none w-full"
              />
            </div>
          </div>

          {/* Clean Responsive Admin Table */}
          <div className="overflow-x-auto">
            {usersLoading ? (
              <div className="p-8 text-center text-xs text-gray-400">Loading user database...</div>
            ) : filteredUsers && filteredUsers.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border-default)] text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                    <th className="py-3.5 px-4">User</th>
                    <th className="py-3.5 px-4">Plan / Role</th>
                    <th className="py-3.5 px-4">Institution</th>
                    <th className="py-3.5 px-4">Activity</th>
                    <th className="py-3.5 px-4 text-center">Resources</th>
                    <th className="py-3.5 px-4 text-center">Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-default)] text-xs">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-[var(--surface-2)]/50 transition">
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-xs text-white shrink-0 shadow-md">
                            {u.full_name?.charAt(0).toUpperCase() || 'U'}
                          </div>
                          <div>
                            <div className="font-bold text-white flex items-center gap-1.5">
                              {u.full_name}
                            </div>
                            <div className="text-[11px] text-gray-400 font-mono">
                              {u.email}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4 space-y-1">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 block w-fit">
                          {u.subscription_tier}
                        </span>
                        <span className="text-[10px] font-mono text-purple-300 block">
                          {u.role || 'STUDENT'}
                        </span>
                      </td>

                      <td className="py-4 px-4 text-gray-300">
                        {u.institution_name || <span className="text-gray-500 italic">Not set</span>}
                      </td>

                      <td className="py-4 px-4 text-[11px] text-gray-400">
                        <div>Created: {new Date(u.created_at).toLocaleDateString()}</div>
                        <div className="text-[10px] text-gray-500">
                          {u.last_login_at ? `Login: ${new Date(u.last_login_at).toLocaleDateString()}` : 'Never logged in'}
                        </div>
                      </td>

                      <td className="py-4 px-4">
                        <div className="flex items-center justify-center gap-2 font-mono text-[11px]">
                          <span title="Notes" className="text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                            📝 {u.notes_count}
                          </span>
                          <span title="PDFs" className="text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                            📄 {u.pdfs_count}
                          </span>
                          <span title="Plans" className="text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                            📅 {u.study_plans_count}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-4 text-center">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                            <UserCheck className="w-3 h-3 text-emerald-400" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-300 border border-rose-500/30">
                            <UserX className="w-3 h-3 text-rose-400" /> Suspended
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-4 text-right space-x-1.5">
                        <button
                          onClick={() => {
                            setInspectingUserId(u.id);
                            setInspectorTab('overview');
                          }}
                          className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 font-bold text-[11px] inline-flex items-center gap-1 transition"
                        >
                          <Eye className="w-3.5 h-3.5" /> Inspect
                        </button>

                        <button
                          onClick={() => setSuspendingUser(u)}
                          className={`p-1.5 rounded-xl border transition inline-flex ${
                            u.is_active
                              ? 'text-amber-400 hover:bg-amber-500/10 border-amber-500/20'
                              : 'text-emerald-400 hover:bg-emerald-500/10 border-emerald-500/20'
                          }`}
                          title={u.is_active ? 'Suspend Account' : 'Restore Account'}
                        >
                          {u.is_active ? <Ban className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
                        </button>

                        <button
                          onClick={() => {
                            setResettingUser(u);
                            setNewPassword('');
                            setResetMsg('');
                            setResetError('');
                          }}
                          className="p-1.5 rounded-xl text-purple-400 hover:bg-purple-500/10 border border-purple-500/20 transition inline-flex"
                          title="Reset User Password"
                        >
                          <KeyRound className="w-4 h-4" />
                        </button>

                        {!u.is_admin && (
                          <button
                            onClick={() => setDeletingUser(u)}
                            className="p-1.5 rounded-xl text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition inline-flex"
                            title="Delete User"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-gray-400">No users found matching search query.</div>
            )}
          </div>
        </div>
      ) : (
        /* Platform Audit Log Section */
        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-3xl p-6 space-y-6 shadow-2xl">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <History className="w-5 h-5 text-purple-400" /> Platform Security Audit Trail
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">Immutable chronological records of administrative operations, security inspection, and system interventions.</p>
          </div>

          <div className="overflow-x-auto">
            {auditLoading ? (
              <div className="p-8 text-center text-xs text-gray-400">Loading audit history...</div>
            ) : auditLogs && auditLogs.length > 0 ? (
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[var(--border-default)] text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Admin Operator</th>
                    <th className="py-3 px-4">Action Event</th>
                    <th className="py-3 px-4">Target User ID</th>
                    <th className="py-3 px-4">IP Address</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-default)]">
                  {auditLogs.map((log: any) => (
                    <tr key={log.id} className="hover:bg-[var(--surface-2)]/50 transition">
                      <td className="py-3 px-4 font-mono text-gray-300">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-bold text-purple-300">
                        {log.admin_email}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-purple-500/10 text-purple-300 border border-purple-500/30">
                          {log.action_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-400">
                        {log.target_user_id || 'System'}
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-500">
                        {log.ip_address || 'Internal API'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-xs text-gray-400">No platform audit logs recorded yet.</div>
            )}
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resettingUser && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <form onSubmit={handleResetSubmit} className="w-full max-w-md bg-[#0d0c15] border border-amber-500/40 rounded-3xl p-6 space-y-4 shadow-2xl animate-in fade-in">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                <KeyRound className="w-4 h-4 text-amber-400 shrink-0" /> Reset User Password
              </div>
              <button type="button" onClick={() => setResettingUser(null)} className="text-gray-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-300">
              Set a new password for <strong className="text-white">{resettingUser.full_name}</strong> (<span className="font-mono text-amber-300">{resettingUser.email}</span>):
            </p>

            {resetMsg && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-400" /> {resetMsg}
              </div>
            )}

            {resetError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-semibold">
                {resetError}
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">New Password</label>
              <input
                type="text"
                required
                placeholder="Enter new password (min 6 chars)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-black/60 border border-white/15 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setResettingUser(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={resetPasswordMutation.isPending || !newPassword.trim()}
                className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-600/30 flex items-center gap-2"
              >
                {resetPasswordMutation.isPending ? 'Updating...' : 'Set Password'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Suspend / Restore Confirmation Modal */}
      {suspendingUser && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#0d0c15] border border-amber-500/40 rounded-3xl p-6 space-y-4 shadow-2xl animate-in fade-in">
            <div className="flex items-center gap-3 text-amber-300 font-bold text-base">
              <Ban className="w-5 h-5 text-amber-400 shrink-0" /> Confirm Account Action
            </div>

            <p className="text-xs text-gray-300 leading-relaxed">
              Are you sure you want to {suspendingUser.is_active ? 'SUSPEND' : 'RESTORE'} user account <strong className="text-white">{suspendingUser.full_name}</strong> (<span className="font-mono text-amber-300">{suspendingUser.email}</span>)?
            </p>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {actionError}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setSuspendingUser(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => toggleSuspendMutation.mutate({ userId: suspendingUser.id, suspend: suspendingUser.is_active })}
                disabled={toggleSuspendMutation.isPending}
                className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-600/30 flex items-center gap-2"
              >
                {toggleSuspendMutation.isPending ? 'Processing...' : suspendingUser.is_active ? 'Suspend Account' : 'Restore Account'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8-Tab User Inspector Slide-Over Drawer */}
      {inspectingUserId && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          <div className="w-full max-w-5xl max-h-[92vh] bg-[#0d0c15] border border-indigo-500/40 rounded-3xl p-6 space-y-6 shadow-2xl flex flex-col justify-between overflow-hidden animate-in fade-in zoom-in-95">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4 shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-lg text-white">
                    User Overview: {inspectedData?.user_info.full_name || 'Loading...'}
                  </h3>
                  <div className="flex items-center gap-3">
                    <p className="text-xs text-gray-400 font-mono">{inspectedData?.user_info.email}</p>
                    <span className="text-[10px] font-mono font-bold text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30">
                      Role: {inspectedData?.user_info.role || 'STUDENT'}
                    </span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setInspectingUserId(null)}
                className="p-2 text-gray-400 hover:text-white rounded-xl transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            {inspectingLoading ? (
              <div className="p-12 text-center text-xs text-gray-400">Fetching user data memory...</div>
            ) : inspectedData ? (
              <div className="flex-1 overflow-y-auto space-y-6 pr-2">
                {/* 8-Tab Navigation Bar */}
                <div className="no-scrollbar flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-white/10 text-xs font-bold">
                  {[
                    { id: 'overview', label: 'Overview', icon: Users },
                    { id: 'academic', label: 'Academic Memory', icon: GraduationCap },
                    { id: 'activity', label: 'Activity Logs', icon: Activity },
                    { id: 'resources', label: 'Resources Vault', icon: BookOpen },
                    { id: 'connections', label: 'Connections Network', icon: Users },
                    { id: 'sessions', label: 'AI Sessions', icon: Clock },
                    { id: 'security', label: 'Security & Role', icon: Lock },
                    { id: 'audit', label: 'Audit Trail', icon: History }
                  ].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setInspectorTab(t.id as any)}
                      className={`px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition shrink-0 border text-[11px] ${
                        inspectorTab === t.id
                          ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                          : 'bg-white/5 text-gray-400 border-transparent hover:text-white'
                      }`}
                    >
                      <t.icon className="w-3.5 h-3.5" />
                      {t.label}
                    </button>
                  ))}
                </div>

                {/* Tab 1: Overview */}
                {inspectorTab === 'overview' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-4 text-xs">
                    <h4 className="font-bold text-white text-sm">Account Overview</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div>
                        <span className="text-gray-400 block text-[11px]">User ID</span>
                        <span className="font-mono text-indigo-300 text-[11px]">{inspectedData.user_info.id}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Account Status</span>
                        <span className="font-bold text-white">{inspectedData.user_info.is_active ? 'Active' : 'Suspended'}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Subscription Tier</span>
                        <span className="font-bold text-purple-300 uppercase">{inspectedData.user_info.subscription_tier}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Joined Date</span>
                        <span className="font-semibold text-white">{new Date(inspectedData.user_info.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 2: Academic */}
                {inspectorTab === 'academic' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-3 text-xs">
                    <h4 className="font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-2">
                      <GraduationCap className="w-4 h-4 text-indigo-400" /> Academic Profile & Enrolled Subjects
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div>
                        <span className="text-gray-400 block text-[11px]">Institution</span>
                        <span className="font-semibold text-white">{inspectedData.user_info.institution_name || 'Not specified'}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Education Level</span>
                        <span className="font-semibold text-white capitalize">{inspectedData.user_info.education_level || 'Not specified'}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Course / Field</span>
                        <span className="font-semibold text-white capitalize">{inspectedData.user_info.field || 'Not specified'}</span>
                      </div>
                      <div>
                        <span className="text-gray-400 block text-[11px]">Specialization</span>
                        <span className="font-semibold text-white">{inspectedData.user_info.specialization || 'General Studies'}</span>
                      </div>
                    </div>

                    <div className="pt-2">
                      <span className="text-gray-400 block text-[11px] mb-1">Enrolled Subjects:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {inspectedData.user_info.subjects.length > 0 ? (
                          inspectedData.user_info.subjects.map((s, idx) => (
                            <span key={idx} className="px-2.5 py-1 rounded-lg text-[11px] bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-500 italic">No enrolled subjects registered.</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 3: Activity */}
                {inspectorTab === 'activity' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-3 text-xs">
                    <h4 className="font-bold text-white text-sm">Platform Activity Logs</h4>
                    <p className="text-gray-400">Last Login: {inspectedData.user_info.last_login_at ? new Date(inspectedData.user_info.last_login_at).toLocaleString() : 'No recorded login history'}</p>
                    <p className="text-gray-400">Onboarding Status: {inspectedData.user_info.onboarding_completed ? 'Completed ✅' : 'Pending ⏳'}</p>
                  </div>
                )}

                {/* Tab 4: Resources */}
                {inspectorTab === 'resources' && (
                  <div className="space-y-4">
                    <h4 className="font-bold text-white text-sm">Authored Notes & Documents</h4>
                    <div className="space-y-2">
                      {inspectedData.notes.map((n) => (
                        <div key={n.id} className="p-3.5 rounded-xl bg-black/50 border border-white/10 flex items-center justify-between text-xs">
                          <div>
                            <h5 className="font-bold text-white">{n.title}</h5>
                            <p className="text-[10px] text-gray-400 font-mono">Source: {n.source} • Words: {n.word_count}</p>
                          </div>
                          <button
                            onClick={() => setViewingNoteContent({ title: n.title, content: n.content })}
                            className="px-3 py-1 rounded-lg bg-purple-600/20 text-purple-300 font-bold text-[11px] border border-purple-500/30 hover:bg-purple-600 hover:text-white transition"
                          >
                            Read Note
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tab 5: Connections */}
                {inspectorTab === 'connections' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-3 text-xs">
                    <h4 className="font-bold text-white text-sm">Peer Network Connections</h4>
                    <p className="text-gray-300">Total Active Connections: <strong className="text-indigo-300">{inspectedData.user_info.connections_count}</strong></p>
                  </div>
                )}

                {/* Tab 6: Sessions */}
                {inspectorTab === 'sessions' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-3 text-xs">
                    <h4 className="font-bold text-white text-sm">AI Tutor Memory & Sessions</h4>
                    <p className="text-gray-400">Total Active Study Plans: {inspectedData.study_plans.length}</p>
                  </div>
                )}

                {/* Tab 7: Security */}
                {inspectorTab === 'security' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-4 text-xs">
                    <h4 className="font-bold text-white text-sm">Security & Access Role Control</h4>
                    <div>
                      <span className="text-gray-400 block text-[11px]">Current Assigned Role</span>
                      <span className="font-mono text-purple-300 text-sm font-bold">{inspectedData.user_info.role || 'STUDENT'}</span>
                    </div>
                    <button
                      onClick={() => {
                        setResettingUser({
                          id: inspectedData.user_info.id,
                          email: inspectedData.user_info.email,
                          full_name: inspectedData.user_info.full_name,
                          is_admin: inspectedData.user_info.is_admin,
                          role: inspectedData.user_info.role,
                          is_active: inspectedData.user_info.is_active,
                          subscription_tier: inspectedData.user_info.subscription_tier,
                          onboarding_completed: inspectedData.user_info.onboarding_completed,
                          notes_count: 0,
                          pdfs_count: 0,
                          study_plans_count: 0,
                          created_at: inspectedData.user_info.created_at
                        });
                        setNewPassword('');
                        setResetMsg('');
                        setResetError('');
                      }}
                      className="px-4 py-2 rounded-xl bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/30 text-amber-300 font-bold text-xs flex items-center gap-1.5 transition"
                    >
                      <KeyRound className="w-4 h-4 text-amber-400" /> Reset User Password
                    </button>
                  </div>
                )}

                {/* Tab 8: Audit Log */}
                {inspectorTab === 'audit' && (
                  <div className="p-5 rounded-2xl bg-[var(--surface-2)] border border-white/10 space-y-3 text-xs">
                    <h4 className="font-bold text-white text-sm">User Specific Audit History</h4>
                    <p className="text-gray-400">View platform audit logs tab for full system-wide history.</p>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Render Note Content Viewer Sub-Modal */}
      {viewingNoteContent && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-3xl max-h-[85vh] bg-[#0d0c15] border border-purple-500/40 rounded-3xl p-6 space-y-4 shadow-2xl flex flex-col justify-between overflow-hidden animate-in fade-in">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="font-bold text-base text-white">{viewingNoteContent.title}</h3>
              <button onClick={() => setViewingNoteContent(null)} className="text-gray-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto pr-2 p-4 bg-black/50 rounded-2xl border border-white/10">
              <MarkdownRenderer content={viewingNoteContent.content} />
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingUser && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#0d0c15] border border-rose-500/40 rounded-3xl p-6 space-y-5 shadow-2xl animate-in fade-in">
            <div className="flex items-center gap-3 text-rose-400 font-bold text-lg">
              <AlertTriangle className="w-6 h-6 shrink-0" /> Confirm User Deletion
            </div>

            <p className="text-xs text-gray-300 leading-relaxed">
              Are you sure you want to permanently delete user <strong className="text-white">{deletingUser.full_name}</strong> (<span className="font-mono text-rose-300">{deletingUser.email}</span>)?
              This will erase all of their authored notes, uploaded PDFs, study plans, and attendance memory.
            </p>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {actionError}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setDeletingUser(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteUserMutation.mutate(deletingUser.id)}
                disabled={deleteUserMutation.isPending}
                className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/30 flex items-center gap-2"
              >
                {deleteUserMutation.isPending ? 'Deleting...' : 'Permanently Delete User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
