<script lang="ts">
  interface Project {
    id: string;
    name: string;
    title: string;
    video_title: string;
    createdAt: string;
    updatedAt: string;
    prompt?: string;
    staticSubtitle?: string;
  }

  export let projects: Project[];
  export let onSelectProject: (project: Project) => void;
  export let onCopyProject: (project: Project) => void;
  export let onDeleteProject: (projectId: string) => void;
  export let onCreateProject: () => void;
</script>

<!-- Projects Tab -->
<div
  class="rounded-2xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-sm"
>
  <div class="flex items-center justify-between mb-6">
    <h2 class="text-xl font-semibold">Your Projects</h2>
    <button
      onclick={onCreateProject}
      class="rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 px-4 py-2 text-white transition-all duration-200 hover:from-blue-600 hover:to-purple-600"
    >
      Create Project
    </button>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {#each projects as project (project.id)}
      <div
        role="button"
        tabindex="0"
        onclick={() => onSelectProject(project)}
        onkeydown={(e) => {
          if (e.key === 'Enter') {
            onSelectProject(project);
          } else if (e.key === ' ') {
            e.preventDefault();
          }
        }}
        onkeyup={(e) => {
          if (e.key === ' ') {
            onSelectProject(project);
          }
        }}
        class="rounded-xl border border-gray-200 bg-white/80 p-4 shadow-sm transition-all duration-200 hover:shadow-md hover:border-blue-300"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1">
            <h3 class="font-medium text-gray-900 truncate">
              {project.title}
            </h3>
            <p class="text-sm text-gray-500 truncate">{project.name}</p>
          </div>
          <div class="flex gap-2">
            <button
              onclick={() => onSelectProject(project)}
              class="text-blue-600 hover:text-blue-800 transition-colors"
              title="View Project"
              aria-label="View Project"
            >
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                ></path>
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                ></path>
              </svg>
            </button>
            <button
              onclick={() => onCopyProject(project)}
              class="text-green-600 hover:text-green-800 transition-colors"
              title="Copy Project"
              aria-label="Copy Project"
            >
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                ></path>
              </svg>
            </button>
            <button
              onclick={() => onDeleteProject(project.id)}
              class="text-red-600 hover:text-red-800 transition-colors"
              title="Delete Project"
              aria-label="Delete Project"
            >
              <svg
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                ></path>
              </svg>
            </button>
          </div>
        </div>
        <div class="text-xs text-gray-400">
          Created: {new Date(project.createdAt).toLocaleDateString()}
        </div>
      </div>
    {:else}
      <div class="col-span-full text-center py-8 text-gray-500">
        <p>No projects yet. Create your first project to get started!</p>
      </div>
    {/each}
  </div>
</div>
