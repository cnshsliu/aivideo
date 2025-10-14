<script lang="ts">
  import { onMount } from 'svelte';

  let {
    showCopyProject,
    copyProjectName = $bindable(''),
    copyProjectTitle = $bindable(''),
    onCopyProject,
    onClose
  } = $props<{
    showCopyProject: boolean;
    copyProjectName?: string;
    copyProjectTitle?: string;
    onCopyProject: () => void;
    onClose: () => void;
  }>();

  let modalElement = $state<HTMLDivElement>();
  let nameError = $state(false);
  let titleError = $state(false);
  let nameFlash = $state(false);
  let titleFlash = $state(false);

  onMount(() => {
    // Generate UUID for project name by default
    copyProjectName = crypto.randomUUID();
  });

  function handleCopy() {
    // Reset error states
    nameError = false;
    titleError = false;
    nameFlash = false;
    titleFlash = false;

    // Trim values and check if empty
    const trimmedName = copyProjectName.trim();
    const trimmedTitle = copyProjectTitle.trim();

    // Set error states for empty fields
    if (!trimmedName) {
      nameError = true;
      nameFlash = true;
    }
    if (!trimmedTitle) {
      titleError = true;
      titleFlash = true;
    }

    if (!trimmedName || !trimmedTitle) {
      return;
    }

    onCopyProject();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleCopy();
    } else if (event.key === 'Escape') {
      onClose();
    }
  }
</script>

<style>
  @keyframes flash-border {
    0%, 100% {
      border-color: rgb(239 68 68); /* red-500 */
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
    }
    50% {
      border-color: rgb(239 68 68);
      box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3);
    }
  }

  .flash-error {
    animation: flash-border 1s ease-in-out infinite;
  }
</style>

{#if showCopyProject}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    onkeydown={handleKeydown}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <div
      bind:this={modalElement}
      class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
    >
      <h2 class="mb-4 text-xl font-semibold">Copy to</h2>

      <div class="space-y-4">
        <div>
          <label
            for="copy-project-name"
            class="mb-1 block text-sm font-medium text-gray-700"
          >
            Project Name
          </label>
          <input
            id="copy-project-name"
            type="text"
            bind:value={copyProjectName}
            required
            minlength="1"
            maxlength="50"
            pattern="[a-zA-Z0-9_-]+"
            class="w-full rounded-lg px-3 py-2 focus:ring-2 {nameError ? `border-2 border-red-500 focus:ring-red-500 ${nameFlash ? 'flash-error' : ''}` : 'border border-gray-300 focus:border-transparent focus:ring-blue-500'}"
            placeholder="unique-project-name"
          />
          <p class="mt-1 text-xs text-gray-500">
            Letters, numbers, underscores, and hyphens only
          </p>
        </div>

        <div>
          <label
            for="copy-project-title"
            class="mb-1 block text-sm font-medium text-gray-700"
          >
            Project Title
          </label>
          <input
            id="copy-project-title"
            type="text"
            bind:value={copyProjectTitle}
            minlength="1"
            maxlength="100"
            class="w-full rounded-lg px-3 py-2 focus:ring-2 {titleError ? `border-2 border-red-500 focus:ring-red-500 ${titleFlash ? 'flash-error' : ''}` : 'border border-gray-300 focus:border-transparent focus:ring-blue-500'}"
            placeholder="My Copied Video Project"
          />
        </div>
      </div>

      <div class="mt-6 flex gap-3">
        <button
          onclick={handleCopy}
          class="flex-1 rounded-lg bg-green-500 py-2 text-white transition-colors hover:bg-green-600"
        >
          Copy Now
        </button>
        <button
          onclick={onClose}
          class="flex-1 rounded-lg bg-gray-300 py-2 text-gray-700 transition-colors hover:bg-gray-400"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
{/if}
