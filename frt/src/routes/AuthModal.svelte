<script lang="ts">
  export let showAuth: boolean;
  export let onClose: () => void;
  export let onLogin: (event: Event) => Promise<void>;

  let error = "";
  let success = "";
  let isSubmitting = false;

  async function handleSubmit(event: Event) {
    event.preventDefault();
    isSubmitting = true;
    error = "";
    success = "";

    try {
      await onLogin(event);
    } catch (err) {
      error = "Network error. Please try again.";
    } finally {
      isSubmitting = false;
    }
  }
</script>

{#if showAuth}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
  >
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <h2 class="mb-4 text-xl font-semibold">Login / Register</h2>

      <div class="mb-4 rounded-lg bg-blue-50 p-3">
        <p class="text-sm text-blue-800">
          <strong>New users:</strong> Enter your desired username and password
          to register automatically.<br />
          <strong>Existing users:</strong> Enter your credentials to login.
        </p>
      </div>

      <div class="mb-4 rounded-lg bg-gray-50 p-3">
        <p class="text-sm text-gray-600">
          <strong>Demo account:</strong> Username:
          <code class="rounded bg-gray-200 px-1">demo</code>, Password:
          <code class="rounded bg-gray-200 px-1">demo123</code>
        </p>
      </div>

      {#if error}
        <div
          class="mb-4 rounded-lg border border-red-400 bg-red-100 p-4 text-red-700"
        >
          {error}
        </div>
      {/if}

      {#if success}
        <div
          class="mb-4 rounded-lg border border-green-400 bg-green-100 p-4 text-green-700"
        >
          {success}
        </div>
      {/if}

      <form onsubmit={handleSubmit}>
        <div class="space-y-4">
          <div>
            <label
              for="username"
              class="mb-1 block text-sm font-medium text-gray-700"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              name="username"
              required
              minlength="3"
              maxlength="31"
              pattern="[a-z0-9_-]+"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              placeholder="3-31 characters, lowercase only"
            />
            <p class="mt-1 text-xs text-gray-500">
              Lowercase letters, numbers, underscores, and hyphens only
            </p>
          </div>

          <div>
            <label
              for="password"
              class="mb-1 block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              name="password"
              required
              minlength="6"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              placeholder="At least 6 characters"
            />
          </div>
        </div>

        <div class="mt-6 flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            class="flex-1 rounded-lg bg-blue-500 py-2 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {#if isSubmitting}
              <div class="flex items-center justify-center space-x-2">
                <div
                  class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
                ></div>
                <span>Processing...</span>
              </div>
            {:else}
              Login / Register
            {/if}
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
