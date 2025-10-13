// Shared storage for all API endpoints
export const mockTasks = new Map();

export const mockUsers = new Map();
export const mockSessions = new Map();

// Add sample task for demonstration
if (mockTasks.size === 0) {
  mockTasks.set('tid_sample123', {
    id: 'sample123',
    userId: 'user1',
    taskId: 'tid_sample123',
    status: 'completed',
    sourceLanguage: 'en',
    targetLanguage: 'zh',
    sourceType: 'text',
    sourceContent: 'Hello, this is a sample translation.',
    markdownPath: '/uploads/tid_sample123.md',
    cost: 0.01,
    createdAt: new Date(Date.now() - 3600000), // 1 hour ago
    completedAt: new Date(Date.now() - 3500000) // 59 minutes ago
  });
}
