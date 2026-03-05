const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("linguacoachDesktop", {
  platform: process.platform,
  version: process.versions.electron,
});
