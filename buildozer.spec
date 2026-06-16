
[app]

title = Advanced AI Shorts Editor
package.name = ai_shorts_editor
package.domain = org.ai

source.dir = .
source.include_exts = py,png,jpg,kv

version = 1.0

requirements = python3,kivy,ffpyplayer

orientation = portrait

fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,INTERNET

android.api = 33
android.minapi = 24
android.archs = arm64-v8a

[buildozer]

log_level = 2
warn_on_root = 1
