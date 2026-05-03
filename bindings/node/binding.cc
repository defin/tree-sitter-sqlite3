#include <napi.h>

typedef struct TSLanguage TSLanguage;

extern "C" TSLanguage *tree_sitter_sqlite3();

Napi::Object Init(Napi::Env env, Napi::Object exports) {
  exports["name"] = Napi::String::New(env, "sqlite3");
  exports["language"] = Napi::External<TSLanguage>::New(
      env, tree_sitter_sqlite3());
  return exports;
}

NODE_API_MODULE(tree_sitter_sqlite3_binding, Init)
