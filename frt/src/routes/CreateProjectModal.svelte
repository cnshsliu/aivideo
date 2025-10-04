<script lang="ts">
  export let showCreateProject: boolean;
  export let newProjectName: string;
  export let newProjectTitle: string;
  export let onCreateProject: () => void;
  export let onClose: () => void;
</script>

{#if showCreateProject}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
  >
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <h2 class="mb-4 text-xl font-semibold">Create New Project</h2>

      <form onsubmit={onCreateProject}>
        <div class="space-y-4">
          <div>
            <label
              for="project-name"
              class="mb-1 block text-sm font-medium text-gray-700"
            >
              Project Name
            </label>
            <input
              id="project-name"
              type="text"
              bind:value={newProjectName}
              required
              minlength="1"
              maxlength="50"
              pattern="[a-zA-Z0-9_-]+"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              placeholder="unique-project-name"
            />
            <p class="mt-1 text-xs text-gray-500">
              Letters, numbers, underscores, and hyphens only
            </p>
          </div>

          <div>
            <label
              for="project-title"
              class="mb-1 block text-sm font-medium text-gray-700"
            >
              Project Title
            </label>
            <input
              id="project-title"
              type="text"
              bind:value={newProjectTitle}
              minlength="1"
              maxlength="100"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              placeholder="My Amazing Video Project"
            />
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            type="submit"
            class="flex-1 rounded-lg bg-blue-500 py-2 text-white transition-colors hover:bg-blue-600"
          >
            Create Project
          </button>
          <button
            type="button"
            onclick={onClose}
            class="flex-1 rounded-lg bg-gray-300 py-2 text-gray-700 transition-colors hover:bg-gray-400"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
