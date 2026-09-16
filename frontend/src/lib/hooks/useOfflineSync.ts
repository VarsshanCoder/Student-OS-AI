import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { offlineDb } from '@/lib/offline-db';
import { apiClient } from '@/lib/api-client';
import { useAppStore } from '@/stores/app-store';

export function useOfflineSync() {
  const queryClient = useQueryClient();
  const user = useAppStore(state => state.user);

  useEffect(() => {
    if (!user) return;
    
    // Background sync function
    const syncData = async () => {
      try {
        if (!navigator.onLine) return;

        // Fetch recent notes and cache locally
        const notesRes = await apiClient.get('/notes?limit=20');
        if (notesRes.data) {
          const formatted = notesRes.data.map((n: any) => ({
            id: n.id,
            title: n.title,
            content: n.content || n.plain_text || '',
            subjectId: n.subject_id,
            tags: n.tags || [],
            updatedAt: n.updated_at,
            isSynced: true
          }));
          await offlineDb.notes.bulkPut(formatted);
        }

        // Fetch recent attendance
        const attendanceRes = await apiClient.get('/attendance');
        if (attendanceRes.data) {
          const attFormatted = attendanceRes.data.map((a: any) => ({
            id: a.id,
            subjectId: a.subject_id,
            date: a.date,
            status: a.status,
            period: a.period_number,
            isSynced: true
          }));
          await offlineDb.attendance.bulkPut(attFormatted);
        }
        
      } catch (e) {
        console.error('Offline sync failed', e);
      }
    };

    // Run sync when online
    syncData();
    window.addEventListener('online', syncData);
    
    return () => {
      window.removeEventListener('online', syncData);
    };
  }, [user]);
}
