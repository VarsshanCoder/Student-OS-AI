# SCHOLAROS — ADMIN PANEL & SCHOLARCONNECT PRODUCTION IMPROVEMENT PLAN

## 1. Executive Summary & Audit Baseline
This plan defines the comprehensive production architecture, security hardening, visual redesign, and feature enhancements for the **ScholarOS Admin Control Center** and **ScholarConnect Academic Collaboration Engine**. 

---

## 2. Current Implementation Audit & Problem Analysis

### A. Admin Panel Audit
- **Exposed Sensitive Passwords**: `User` model & `/admin/users` API returned `raw_password` in plain text.
- **Lack of Role-Based Access Control (RBAC)**: Authentication currently relies solely on a binary `is_admin: bool` flag instead of explicit hierarchical roles (`SUPER_ADMIN`, `ADMIN`, `MODERATOR`, `STUDENT`).
- **No Audit Logging**: Administrative operations (user inspection, password reset, account deletion, status changes) operate silently without persistent audit trails.
- **Cramped UI Layout**: Admin table attempts to display all user attributes in tight table columns, causing text overlap and readability issues on lower resolution screens.
- **Missing Account Control Actions**: Lacks account suspension (`is_active = False`), role elevation/demotion, and detailed multi-tab user slide-over panels.

### B. ScholarConnect Audit
- **Tab Bloat**: Contained legacy/redundant tabs (`Voice Lounge`, `AI Buddy Match`, `Peer Progress Feed`).
- **Incomplete Friend Relationship States**: Lacked explicit database-backed `blocked`, `pending_received`, and `cancelled` connection lifecycle tracking.
- **Unrestricted Student Directory & Privacy Deficits**: Lacked user privacy preferences (`Who can find me?`).
- **Generic Recommendation Explanations**: Lacked explicit contextual matching rationales (e.g. mutual subjects, institution, course).
- **Resource Permission Leak Potential**: Sharing a note previously lacked strict resource-level access control tokens (`view_only`, `can_duplicate`, `can_collaborate`).
- **Direct Messaging UI Deficits**: Lacked a side panel for quick access to shared files/notes, message delivery status indicators (`sent`, `delivered`, `read`), and offline retry handling.

---

## 3. Database Schema Migrations

```sql
-- 1. RBAC and User Status Fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'STUDENT' NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS discovery_setting VARCHAR(20) DEFAULT 'anyone' NOT NULL; -- anyone, my_institution, invite_link, nobody
ALTER TABLE users DROP COLUMN IF EXISTS raw_password;

-- 2. Audit Logs Table
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    admin_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL, -- USER_VIEWED, USER_SUSPENDED, USER_RESTORED, USER_DELETED, USER_PASSWORD_RESET, ROLE_CHANGED
    target_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    details_json JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_admin ON admin_audit_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_target ON admin_audit_logs(target_user_id);

-- 3. Enhanced Friend Connection Table
ALTER TABLE user_connections ADD COLUMN IF NOT EXISTS blocked_by_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE;

-- 4. Shared Resource Permissions Table
CREATE TABLE IF NOT EXISTS resource_shares (
    id VARCHAR(36) PRIMARY KEY,
    owner_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    shared_with_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE, -- NULL for public/group share
    group_id VARCHAR(36) REFERENCES connect_groups(id) ON DELETE CASCADE,
    resource_type VARCHAR(30) NOT NULL, -- note, pdf, flashcard, mindmap, quiz, study_plan
    resource_id VARCHAR(36) NOT NULL,
    permission VARCHAR(20) DEFAULT 'view_only' NOT NULL, -- view_only, can_duplicate, can_collaborate
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resource_shares_owner ON resource_shares(owner_id);
CREATE INDEX IF NOT EXISTS idx_resource_shares_target ON resource_shares(shared_with_id);
```

---

## 4. Admin Panel Architecture & UI Redesign

### Recommended Table Structure
```
| User (Avatar, Name, @username) | Plan | Institution | Activity (Status / Last Login) | Resources (Count) | Status | Actions |
```

### User Detail Slide-Over Panel (8 Tabs)
1. **Overview**: Essential account info, user ID, registered date, current role, subscription tier.
2. **Academic**: Institution name, education level, field of study, specialization, enrolled subjects.
3. **Activity**: Login history, total active time, notes created, study plan completion rates.
4. **Resources**: Inspected authored notes, uploaded PDFs, study schedules (with modal viewer).
5. **Connections**: Active peer connections, sent/received requests, blocked status.
6. **Sessions**: Active AI tutor sessions, academic memory logs, reputation score.
7. **Security**: Password reset, role assignment (`SUPER_ADMIN`, `ADMIN`, `MODERATOR`, `STUDENT`), active session revocation.
8. **Audit Log**: Complete chronological audit trail of all admin interventions on this account.

### Strict Destructive Action Workflows
- **Account Deletion / Suspension**: Requires 2-step confirmation modal explicitly detailing data consequences, requiring manual confirmation input before dispatching API calls.

---

## 5. ScholarConnect Academic Collaboration Architecture

### Primary Navigation (3 Main Modes)
1. **`👥 Friends`**: Search classmates, peer discovery directory, connection management (`Accepted`, `Pending`, `Received`, `Blocked`).
2. **`💬 Messages`**: 1-on-1 encrypted private direct messages with real-time WebSocket delivery, message status tracking (`sending`, `sent`, `delivered`, `read`), and shared resource side drawer.
3. **`📚 Study Groups`**: Collaborative group study workspaces, shared notes, group chat, live whiteboards, and assignment coordination.

### Profile Discovery & Privacy Settings
Students can set their visibility in Settings:
- `anyone`: Visible in global classmate search & recommendations.
- `my_institution`: Visible only to students in the same institution.
- `invite_link`: Hidden from directory; searchable only via exact link/ID.
- `nobody`: Completely hidden from discovery & recommendations.

### Contextual "Suggested Study Partners"
Recommendations display explicit academic matching rationales:
- *"Suggested because you both study B.Sc AI & ML (Semester 1)"*
- *"Suggested because you share 3 enrolled subjects: Machine Learning, Linear Algebra, Python"*

---

## 6. Testing & Quality Assurance Strategy

### E2E Automation (Playwright)
- **Multi-Account Scenarios**: Uses isolated test accounts (`QA Student A`, `QA Student B`, `QA Admin`).
- **Friend Lifecycle Test**: Search -> Request -> Accept -> DM -> Share Resource -> Block -> Unblock.
- **RBAC Security Verification**: Verifies `STUDENT` account receives HTTP 403 Forbidden on all `/api/v1/admin/*` endpoints.

### Responsive Viewport Verification
- **Mobile**: 320px, 360px, 375px, 390px, 412px, 430px.
- **Desktop**: 1366x768, 1440x900, 1920x1080.

---

## 7. Task Categorization & Implementation Order

### P0 Critical (Security & Core Integrity)
1. Remove `raw_password` storage and API response leaks.
2. Implement backend RBAC decorator/middleware (`require_role`).
3. Enforce server-side resource-level permission checks for shared notes/files.
4. Implement persistent `AdminAuditLog` tracking in backend database.

### P1 High (Core Features & Admin Redesign)
5. Build new responsive Admin Table & 8-tab User Detail Slide-Over Panel.
6. Implement Friend System state machine (`none`, `pending_sent`, `pending_received`, `accepted`, `blocked`).
7. Build 1-on-1 Direct Messaging with Shared Resource Side Drawer & status indicators.
8. Enforce Privacy Settings (`discovery_setting`) in classmate search and recommendations.

### P2 Medium (Workspaces & Enhancements)
9. Upgrade Study Groups with shared resource libraries and member role management.
10. Contextual "Suggested Study Partners" with explicit mutual subject/course badges.
11. Mobile UX optimization (Bottom sheets & card layout transformation).

### P3 Polish & Testing
12. Comprehensive E2E Playwright test suite for Admin & ScholarConnect workflows.
13. Responsive screenshot audit across 9 screen viewports.
14. Generate `ADMIN_CONNECT_QA_REPORT.md`.
