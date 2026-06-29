import * as constants from "./constants.js";

import { createRouter, createWebHistory } from "vue-router";

import { authCheck } from "./api.js";

const router = createRouter({
  history: createWebHistory(""),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("./views/Home.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("./views/LogIn.vue"),
      props: (route) => ({ redirect: route.query[constants.params.redirect] }),
    },
    {
      // Support nested paths like /note/folder/subfolder/title
      path: "/note/:title(.*)+",
      name: "note",
      component: () => import("./views/Note.vue"),
      props: (route) =>
        ({ title: Array.isArray(route.params.title)
            ? route.params.title.join("/")
            : route.params.title }),
    },
    {
      path: "/new",
      name: "new",
      component: () => import("./views/Note.vue"),
    },
    {
      path: "/search",
      name: "search",
      component: () => import("./views/SearchResults.vue"),
      props: (route) => ({
        searchTerm: route.query[constants.params.searchTerm],
        sortBy: Number(route.query[constants.params.sortBy]) || undefined,
      }),
    },
  ],
});

let authChecked = false;
router.beforeEach(async (to) => {
  if (authChecked || to.name === "login") {
    return;
  }
  try {
    await authCheck();
    return;
  } catch (error) {
    if (error.response && error.response.status === 401) {
      return {
        name: "login",
        query: { [constants.params.redirect]: to.fullPath },
      };
    }
  } finally {
    authChecked = true;
  }
});

router.afterEach((to) => {
  let title = "flatnotes";
  if (to.name === "note") {
    const noteTitle = Array.isArray(to.params.title)
      ? to.params.title.join("/")
      : to.params.title;
    if (noteTitle) {
      // Show only the last segment in the browser tab
      const lastSegment = noteTitle.split("/").pop();
      title = `${lastSegment} - ${title}`;
    } else {
      title = "New Note - " + title;
    }
  }
  document.title = title;
});

export default router;
