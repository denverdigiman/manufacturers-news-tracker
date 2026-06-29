<template>
  <LoadingIndicator ref="loadingIndicator" class="flex h-screen flex-col">
    <PrimeToast />
    <SearchModal v-model="isSearchModalVisible" />

    <!-- Top navbar (always full-width) -->
    <NavBar
      v-if="showNavBar"
      class="px-2 pt-4 print:hidden"
      :class="{ 'print:hidden': route.name == 'note' }"
      :hide-logo="!showNavBarLogo"
      @toggleSearchModal="toggleSearchModal"
    />

    <!-- Main area: sidebar + content -->
    <div class="flex min-h-0 flex-1 overflow-hidden">
      <!-- Directory sidebar (always visible except login) -->
      <aside
        v-if="showNavBar"
        class="hidden w-56 shrink-0 flex-col overflow-y-auto border-r border-theme-border bg-theme-background px-2 py-2 md:flex print:hidden"
      >
        <div class="mb-2 flex items-center justify-between px-1">
          <span class="text-xs font-bold uppercase text-theme-text-very-muted">
            Notes
          </span>
          <button
            v-if="globalStore.config.authType !== authTypes.readOnly"
            title="New Note"
            class="rounded p-0.5 text-theme-text-muted hover:text-theme-brand"
            @click="router.push({ name: 'new' })"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 11h-6V5h-2v6H5v2h6v6h2v-6h6z" />
            </svg>
          </button>
        </div>
        <DirectoryTree
          :nodes="tree"
          :activeNotePath="activeNotePath"
          @navigate="navigateToNote"
        />
      </aside>

      <!-- Page content -->
      <div class="flex min-w-0 flex-1 flex-col overflow-y-auto px-2 py-2">
        <RouterView />
      </div>
    </div>
  </LoadingIndicator>
</template>

<script setup>
import Mousetrap from "mousetrap";
import "mousetrap/plugins/global-bind/mousetrap-global-bind";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

import { apiErrorHandler, getConfig, getTree } from "./api.js";
import DirectoryTree from "./components/DirectoryTree.vue";
import LoadingIndicator from "./components/LoadingIndicator.vue";
import PrimeToast from "./components/PrimeToast.vue";
import { authTypes } from "./constants.js";
import { useGlobalStore } from "./globalStore.js";
import { loadTheme } from "./helpers.js";
import NavBar from "./partials/NavBar.vue";
import SearchModal from "./partials/SearchModal.vue";
import router from "./router.js";

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const route = useRoute();
const toast = useToast();
const tree = ref([]);

Mousetrap.bind("/", () => {
  if (route.name !== "login") {
    toggleSearchModal();
    return false;
  }
});

Mousetrap.bindGlobal("ctrl+alt+n", () => {
  if (route.name !== "login") {
    router.push({ name: "new" });
    return false;
  }
});

Mousetrap.bindGlobal("ctrl+alt+h", () => {
  if (route.name !== "login") {
    router.push({ name: "home" });
    return false;
  }
});

function loadTree() {
  getTree()
    .then((data) => { tree.value = data; })
    .catch(() => {}); // non-fatal
}

getConfig()
  .then((data) => {
    globalStore.config = data;
    loadingIndicator.value.setLoaded();
    loadTree();
  })
  .catch((error) => {
    apiErrorHandler(error, toast);
    loadingIndicator.value.setFailed();
  });

// Refresh tree on every route change so create/rename/delete stays in sync
watch(() => route.fullPath, loadTree);

const showNavBar = computed(() => route.name !== "login");
const showNavBarLogo = computed(() => route.name !== "home");

const activeNotePath = computed(() => {
  if (route.name !== "note") return null;
  const t = route.params.title;
  return Array.isArray(t) ? t.join("/") : t;
});

function navigateToNote(path) {
  router.push({ name: "note", params: { title: path } });
}

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}

loadTheme();
</script>
