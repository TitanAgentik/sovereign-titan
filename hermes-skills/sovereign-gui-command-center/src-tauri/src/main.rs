#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // --- SOVEREIGN TITAN: NVIDIA WebKitGTK & HiDPI Stabilization ---
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
    std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
    std::env::set_var("__NV_DISABLE_EXPLICIT_SYNC", "1");
    std::env::set_var("GDK_SCALE", "1");
    std::env::set_var("GDK_DPI_SCALE", "1");

    sovereign_gui_command_center_lib::run();
}
