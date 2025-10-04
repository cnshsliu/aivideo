<script lang="ts">
	/* eslint-disable svelte/no-navigation-without-resolve */
	import { fade, slide } from 'svelte/transition';
	import type { TranslationTask } from '$lib/server/db/schema';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	// Use $props() with 'data' prop for SvelteKit page components in Svelte 5 runes mode
	let { data } = $props<{ data: { tid: string } }>();

	// Use Svelte 5 Runes for reactive state
	let task = $state<TranslationTask>({
		id: 'loading',
		taskId: 'loading',
		status: 'unknown',
		sourceLanguage: 'en',
		targetLanguage: 'zh',
		sourceType: 'text',
		sourceContent: null,
		sourceFilePath: null,
		markdownPath: null,
		docxPath: null,
		pdfPath: null,
		pptxPath: null,
		referenceDocId: null,
		cost: '0.00',
		errorMessage: null,
		batchId: null,
		createdAt: new Date(),
		startedAt: null,
		completedAt: null,
		userId: 'temp'
	});
	let error = $state('');
	let translatedContent = $state('');
	let isLoadingTask = $state(false); // Prevent concurrent task loading

	// Load task immediately when component mounts
	// Load task on client mount to avoid SSR fetch issues
	onMount(() => {
		if (data.tid && task.taskId === 'loading') {
			console.log('🔄 [TASK PAGE] Loading task for TID:', data.tid);
			loadTask(data.tid);
		}
	});

	async function loadTask(taskId: string) {
		// Prevent concurrent task loading
		if (isLoadingTask) {
			console.log('🔄 [TASK PAGE] Task already loading, skipping...');
			return;
		}

		// Don't load if task is already completed
		if (task && task.status === 'completed') {
			console.log('🔄 [TASK PAGE] Task already completed, skipping load...');
			return;
		}

		console.log('🔄 [TASK PAGE] Loading task:', taskId);
		isLoadingTask = true;
		error = '';
		try {
			const response = await fetch(`/api/task/${taskId}`);
			if (response.ok) {
				const newTask = await response.json();
				console.log('✅ [TASK PAGE] Task loaded successfully:', newTask.status);
				// Update task reactively
				task = newTask;
				// Load translated content if task is completed
				if (task && task.status === 'completed') {
					console.log('🎯 [TASK PAGE] Task completed, loading translation content...');
					if (task.markdownPath) {
						await loadTranslatedContent();
					} else if (task.sourceContent) {
						// Use sourceContent as translated content (for simple processor)
						translatedContent = task.sourceContent;
						console.log(
							'📝 [TASK PAGE] Translation content loaded from sourceContent, length:',
							translatedContent.length
						);
					}
				}
			} else {
				console.error('❌ [TASK PAGE] Task not found:', taskId);
				error = 'Task not found';
			}
		} catch (err) {
			console.error('❌ [TASK PAGE] Failed to load task:', err);
			error = 'Failed to load task';
		} finally {
			isLoadingTask = false;

			if (task && task.status !== 'completed') {
				console.log('🔄 [TASK PAGE] Task not completed, scheduling reload...');
				setTimeout(() => {
					loadTask(data.tid);
				}, 2000);
			}
		}
	}

	async function loadTranslatedContent() {
		if (task.taskId === 'loading') return; // Guard against null task
		try {
			// In a real app, you'd fetch the content via an API endpoint
			const response = await fetch(`/api/download/${task.id}?format=markdown`);
			if (response.ok) {
				translatedContent = await response.text();
			}
		} catch (err) {
			console.error('Failed to load translated content:', err);
		}
	}

	function getLanguageName(code: string): string {
		const languages: Record<string, string> = {
			en: 'English',
			zh: 'Chinese',
			yue: 'Cantonese',
			auto: 'Auto-detect'
		};
		return languages[code] || code;
	}

	function getStatusColor(status: string): string {
		const colors: Record<string, string> = {
			pending: 'bg-gray-100 text-gray-800',
			processing: 'bg-yellow-100 text-yellow-800',
			completed: 'bg-green-100 text-green-800',
			failed: 'bg-red-100 text-red-800'
		};
		if (status) return colors[status] || 'bg-gray-100 text-gray-800';
		else return 'bg-gray-100 text-gray-800';
	}
	function navigateToHome() {
		goto('/');
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
	<div class="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
		<!-- Header -->
		<div class="mb-8">
			<button onclick={navigateToHome} class="mb-4 inline-block text-blue-600 hover:text-blue-800">
				← Back to Translation Service
			</button>
			<h1
				class="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-3xl font-bold text-transparent"
			>
				Translation Task Details
			</h1>
		</div>

		<!-- Loading State -->
		{#if error}
			<div
				transition:fade={{ duration: 300 }}
				class="rounded-lg border border-red-200 bg-red-50 p-6"
			>
				<h2 class="mb-2 text-lg font-semibold text-red-800">Error</h2>
				<p class="text-red-600">{error}</p>
			</div>
		{:else if task}
			<!-- Task Details -->
			<div
				class="mb-6 rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
			>
				<div class="mb-6 flex flex-wrap gap-4">
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-600">Task ID:</span>
						<code class="rounded bg-gray-100 px-2 py-1 text-sm">{task.id}</code>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-600">Status:</span>
						<span class="rounded-full px-2 py-1 text-xs font-medium {getStatusColor(task.status)}">
							{task.status}
						</span>
						{#if task.status === 'pending' || task.status === 'processing'}
							<div
								transition:slide={{ duration: 200 }}
								class="flex items-center gap-1 rounded bg-blue-100 px-2 py-1 text-xs text-blue-800"
							>
								<div
									class="h-2 w-2 animate-spin rounded-full border border-blue-600 border-t-transparent"
								></div>
								Live updating...
							</div>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-600">Created:</span>
						<span class="text-sm">{new Date(task.createdAt!).toLocaleString()}</span>
					</div>
					{#if task.completedAt}
						<div class="flex items-center gap-2">
							<span class="text-sm font-medium text-gray-600">Completed:</span>
							<span class="text-sm">{new Date(task.completedAt).toLocaleString()}</span>
						</div>
					{/if}
				</div>
				<div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
					<div>
						<span class="text-sm font-medium text-gray-600">Source Language:</span>
						<p class="text-lg font-semibold">{getLanguageName(task.sourceLanguage)}</p>
					</div>
					<div>
						<span class="text-sm font-medium text-gray-600">Target Language:</span>
						<p class="text-lg font-semibold">{getLanguageName(task.targetLanguage)}</p>
					</div>
					<div>
						<span class="text-sm font-medium text-gray-600">Source Type:</span>
						<p class="text-sm">{task.sourceType}</p>
					</div>
					<div>
						<span class="text-sm font-medium text-gray-600">Cost:</span>
						<p class="text-sm font-semibold">${task.cost}</p>
					</div>
				</div>
				{#if task.status === 'failed' && task.errorMessage}
					<div class="rounded-lg border border-red-200 bg-red-50 p-4">
						<h3 class="mb-2 font-semibold text-red-800">Error Details</h3>
						<p class="text-sm text-red-600">{task.errorMessage}</p>
					</div>
				{/if}
			</div>

			<!-- Translation Result -->
			{#if task.status === 'completed'}
				<div
					transition:fade={{ duration: 500 }}
					class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
				>
					<div class="mb-4 flex items-center justify-between">
						<h2 class="text-xl font-semibold">Translation Result</h2>
						<div class="flex gap-2">
							<a
								href={`/api/download/${task.id}?format=markdown`}
								download
								data-sveltekit-reload
								class="rounded-lg bg-blue-500 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-600"
							>
								Download MD
							</a>
							{#if task.docxPath}
								<a
									href={`/api/download/${task.id}?format=docx`}
									download
									data-sveltekit-reload
									class="rounded-lg bg-green-500 px-4 py-2 text-sm text-white transition-colors hover:bg-green-600"
								>
									Download DOCX
								</a>
							{/if}
							{#if task.pdfPath}
								<a
									href={`/api/download/${task.id}?format=pdf`}
									download
									data-sveltekit-reload
									class="rounded-lg bg-red-500 px-4 py-2 text-sm text-white transition-colors hover:bg-red-600"
								>
									Download PDF
								</a>
							{/if}
						</div>
					</div>
					{#if translatedContent}
						<div transition:slide={{ duration: 300 }} class="prose max-w-none whitespace-pre-wrap">
							{translatedContent}
						</div>
					{:else}
						<div class="py-8 text-center">
							<p class="text-gray-500">Translation content not available</p>
						</div>
					{/if}
				</div>
			{:else if task.status === 'processing'}
				<div
					transition:fade={{ duration: 400 }}
					class="rounded-2xl border border-white/20 bg-white/60 p-8 text-center shadow-lg backdrop-blur-sm"
				>
					<div
						class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"
					></div>
					<h3 class="mb-2 text-lg font-semibold">Translation in Progress</h3>
					<p class="text-gray-600">
						Your translation is being processed. This may take a few moments...
					</p>
					<p class="mt-2 text-sm text-gray-500">Task ID: {task.id}</p>
				</div>
			{:else if task.status === 'pending'}
				<div
					transition:fade={{ duration: 400 }}
					class="rounded-2xl border border-white/20 bg-white/60 p-8 text-center shadow-lg backdrop-blur-sm"
				>
					<div class="mb-4 text-yellow-500">
						<svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
					</div>
					<h3 class="mb-2 text-lg font-semibold">Translation Pending</h3>
					<p class="text-gray-600">Your translation is queued and will start processing soon.</p>
					<p class="mt-2 text-sm text-gray-500">Task ID: {task.id}</p>
				</div>
			{/if}
		{:else}
			<div
				class="rounded-2xl border border-white/20 bg-white/60 p-8 text-center shadow-lg backdrop-blur-sm"
			>
				<h2 class="mb-4 text-xl font-semibold">No Task Found</h2>
				<p class="mb-4 text-gray-600">Please check the task ID or return to the main page.</p>
				<a
					href="/"
					data-sveltekit-reload
					class="rounded-lg bg-blue-500 px-4 py-2 text-white transition-colors hover:bg-blue-600"
				>
					Go to Translation Service
				</a>
			</div>
		{/if}
	</div>
</div>
