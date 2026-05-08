// src/adapters/callback.js
function createCallbackAdapter(flushFn, { maxBuffer = 50 } = {}) {
  const buffer = [];
  return {
    onEpisode(episode) {
      buffer.push(episode);
      if (buffer.length >= maxBuffer) {
        this.flush();
      }
    },
    onClick(click) {
      buffer.push({ ...click.episode, click: true });
    },
    flush() {
      if (buffer.length === 0) return;
      const batch = buffer.splice(0);
      flushFn(batch);
    },
    getBuffer() {
      return [...buffer];
    }
  };
}
export {
  createCallbackAdapter
};
