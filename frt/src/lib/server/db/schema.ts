import {
  pgTable,
  integer,
  text,
  timestamp,
  boolean,
  decimal
} from 'drizzle-orm/pg-core';

export const user = pgTable('user', {
  id: text('id').primaryKey(),
  age: integer('age'),
  username: text('username').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  balance: decimal('balance', { precision: 10, scale: 2 }).default('0.00')
});

export const session = pgTable('session', {
  id: text('id').primaryKey(),
  userId: text('user_id')
    .notNull()
    .references(() => user.id),
  expiresAt: timestamp('expires_at', {
    withTimezone: true,
    mode: 'date'
  }).notNull()
});

export const referenceDoc = pgTable('reference_doc', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  filePath: text('file_path').notNull(),
  isPublic: boolean('is_public').default(false),
  userId: text('user_id')
    .notNull()
    .references(() => user.id),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow()
});

export const translationTask = pgTable('translation_task', {
  id: text('id').primaryKey(),
  userId: text('user_id').references(() => user.id),
  taskId: text('task_id').notNull().unique(),
  status: text('status').notNull().default('pending'),
  sourceLanguage: text('source_language').notNull(),
  targetLanguage: text('target_language').notNull(),
  sourceType: text('source_type').notNull(),
  sourceContent: text('source_content'),
  sourceFilePath: text('source_file_path'),
  originalFileName: text('original_file_name'),
  originalFileExtension: text('original_file_extension'),
  markdownPath: text('markdown_path'),
  docxPath: text('docx_path'),
  pdfPath: text('pdf_path'),
  pptxPath: text('pptx_path'),
  referenceDocId: text('reference_doc_id').references(() => referenceDoc.id),
  cost: decimal('cost', { precision: 10, scale: 2 }).default('0.00'),
  errorMessage: text('error_message'),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow(),
  startedAt: timestamp('started_at', { withTimezone: true, mode: 'date' }),
  completedAt: timestamp('completed_at', { withTimezone: true, mode: 'date' })
});

// task_batch table removed - continuous processing doesn't need manual batches

export const taskQueue = pgTable('task_queue', {
  id: text('id').primaryKey(),
  taskId: text('task_id')
    .notNull()
    .references(() => translationTask.taskId),
  queueStatus: text('queue_status').notNull().default('queued'),
  priority: integer('priority').notNull().default(0),
  scheduledAt: timestamp('scheduled_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow(),
  startedAt: timestamp('started_at', { withTimezone: true, mode: 'date' }),
  completedAt: timestamp('completed_at', { withTimezone: true, mode: 'date' }),
  attempts: integer('attempts').notNull().default(0),
  maxAttempts: integer('max_attempts').notNull().default(3),
  errorMessage: text('error_message'),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow()
});

export const project = pgTable('project', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  title: text('title').notNull(),
  video_title: text('video_title'),
  userId: text('user_id')
    .notNull()
    .references(() => user.id),
  prompt: text('prompt'),
  staticSubtitle: text('static_subtitle'),
  desc: text('desc'),
  brief: text('brief'),
  bodytext: text('bodytext').default(''),
  bodytextLength: integer('bodytext_length').default(0),
  keepTitle: boolean('keep_title').default(true),
  openAfterGeneration: boolean('open_after_generation').default(true),
  addTimestampToTitle: boolean('add_timestamp_to_title').default(false),
  titleFont: text('title_font').default('Arial'),
  titleFontSize: integer('title_font_size').default(24),
  titlePosition: integer('title_position').default(50),
  sortOrder: text('sort_order').default('alphnum'),
  keepClipLength: boolean('keep_clip_length').default(false),
  clipNum: integer('clip_num'),
  subtitleFont: text('subtitle_font').default('Arial'),
  subtitleFontSize: integer('subtitle_font_size').default(24),
  subtitlePosition: integer('subtitle_position').default(50),
  genSubtitle: boolean('gen_subtitle').default(true),
  genVoice: boolean('gen_voice').default(false),
  llmProvider: text('llm_provider').default('qwen'),
  bgmFile: text('bgm_file'),
  bgmFadeIn: decimal('bgm_fade_in', { precision: 3, scale: 1 }).default('0.5'),
  bgmFadeOut: decimal('bgm_fade_out', { precision: 3, scale: 1 }).default(
    '0.5'
  ),
  bgmVolume: decimal('bgm_volume', { precision: 2, scale: 1 }).default('0.5'),
  commonPrompt: text('common_prompt').default('文字自然流畅，适合口播'),
  // Progress fields
  progressStep: text('progress_step', {
    enum: ['preparing', 'running', 'complete', 'error']
  }),
  progressCommand: text('progress_command'),
  progressResult: text('progress_result'),
  progressLog: text('progress_log'),
  progressCreatedAt: timestamp('progress_created_at', {
    withTimezone: true,
    mode: 'date'
  }),
  progressUpdatedAt: timestamp('progress_updated_at', {
    withTimezone: true,
    mode: 'date'
  }),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow(),
  updatedAt: timestamp('updated_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow()
});

export const payment = pgTable('payment', {
  id: text('id').primaryKey(),
  userId: text('user_id')
    .notNull()
    .references(() => user.id),
  amount: decimal('amount', { precision: 10, scale: 2 }).notNull(),
  method: text('method').notNull(),
  transactionId: text('transaction_id').unique(),
  status: text('status').notNull().default('pending'),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow(),
  completedAt: timestamp('completed_at', { withTimezone: true, mode: 'date' })
});

export type Session = typeof session.$inferSelect;
export type User = typeof user.$inferSelect;
export type ReferenceDoc = typeof referenceDoc.$inferSelect;
export type TranslationTask = typeof translationTask.$inferSelect;
export type TaskQueue = typeof taskQueue.$inferSelect;
export type Project = typeof project.$inferSelect;
export type Payment = typeof payment.$inferSelect;

export const material = pgTable('material', {
  id: text('id').primaryKey(),
  projectId: text('project_id')
    .notNull()
    .references(() => project.id, { onDelete: 'cascade' }),
  relativePath: text('relative_path').notNull(), // Relative to vaultPath, e.g., "public/media/image.jpg" or "username/media/video.mp4"
  fileName: text('file_name').notNull(),
  fileType: text('file_type').notNull(), // "image", "video", "audio"
  alias: text('alias'), // Optional alias for the material
  isCandidate: boolean('is_candidate').default(true),
  createdAt: timestamp('created_at', {
    withTimezone: true,
    mode: 'date'
  }).defaultNow()
});

export type Material = typeof material.$inferSelect;
