// This is a build script that Cargo will run before compiling the main application.
// Its purpose is to embed the application icon into the final .exe on Windows.

fn main() {
    // We only need to run this script when targeting Windows.
    if cfg!(target_os = "windows") {
        // Use the `winres` crate to create a new Windows resource object.
        let mut res = winres::WindowsResource::new();

        // Set the icon for the executable.
        // It looks for the icon file relative to the project's root directory.
        res.set_icon("assets/beep_boop_baap-rounded.ico");

        // Compile the resource file and link it to the executable.
        res.compile().expect("Failed to compile Windows resource file.");
    }
}

