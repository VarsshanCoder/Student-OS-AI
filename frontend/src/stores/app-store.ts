import { create } from 'zustand';

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  avatar_url?: string;
  avatarUrl?: string;
  preferredLanguage: 'en' | 'ta' | 'tanglish';
  subscriptionTier: 'free' | 'scholar' | 'scholar_pro';
  is_admin?: boolean;
  onboardingCompleted: boolean;
  // Academic memory fields
  educationLevel?: string;
  field?: string;
  specialization?: string;
  institutionName?: string;
  durationYears?: number;
  currentYear?: number;
  currentSemester?: number;
  subjects?: string[];
}

interface AppState {
  user: UserProfile | null;
  sidebarOpen: boolean;
  theme: 'dark' | 'light';
  language: 'en' | 'ta' | 'tanglish';
  reducedPerformance: boolean;
  setUser: (user: UserProfile | null) => void;
  toggleSidebar: () => void;
  setLanguage: (lang: 'en' | 'ta' | 'tanglish') => void;
  setReducedPerformance: (val: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  sidebarOpen: true,
  theme: 'dark',
  language: 'en',
  reducedPerformance: typeof window !== 'undefined' ? 
    (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) : false,
  setUser: (user) => set({ user }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setLanguage: (language) => set({ language }),
  setReducedPerformance: (val) => set({ reducedPerformance: val }),
}));
