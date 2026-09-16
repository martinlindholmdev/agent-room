#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde_json::{json, Value};
use std::{path::PathBuf, process::{Child, Command, Stdio}, sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}}, time::Duration};
use tauri::{Manager, WindowEvent};

struct Runtime { root: PathBuf, child: Arc<Mutex<Option<Child>>>, stopping: Arc<AtomicBool> }

fn launch(binary: &PathBuf, root: &PathBuf) -> std::io::Result<Child> {
    Command::new(binary).arg("--home").arg(root).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn()
}

#[tauri::command]
async fn control(state: tauri::State<'_, Runtime>, action: String, data: Value) -> Result<Value,String> {
    // The renderer gets only this action allowlist, no arbitrary URLs or shell.
    const ALLOWED: &[&str] = &["snapshot","create","join-request","join-finish","bind","request-create","request-decide","send","object","pause","pair-create","pair-approve","revoke","cancel","backup","unlock"];
    if !ALLOWED.contains(&action.as_str()) { return Err("Unsupported action".into()); }
    let ready: Value = serde_json::from_slice(&std::fs::read(state.root.join("ready.json")).map_err(|_| "Starting local helper…")?).map_err(|_| "Helper is restarting")?;
    let port = ready["port"].as_u64().ok_or("Helper port missing")?;
    let token = ready["token"].as_str().ok_or("Helper connection missing")?;
    let client = reqwest::Client::builder().no_proxy().redirect(reqwest::redirect::Policy::none()).timeout(Duration::from_secs(35)).build().map_err(|_| "Connection unavailable")?;
    let response = client.post(format!("http://127.0.0.1:{port}/control")).bearer_auth(token).json(&json!({"action":action,"data":data})).send().await.map_err(|_| "Local helper is reconnecting. Saved messages are retained.")?;
    response.json().await.map_err(|_| "Invalid helper response".into())
}

#[tauri::command]
fn runtime_info(state: tauri::State<'_, Runtime>) -> Value {
    let ready: Value = std::fs::read(state.root.join("ready.json")).ok().and_then(|v| serde_json::from_slice(&v).ok()).unwrap_or(json!({}));
    json!({"home":state.root,"hub_port":ready["hub_port"],"version":"0.1.0","login_start":login_path().map(|p|p.exists()).unwrap_or(false),"updates":"Manual updates; signed release service not configured"})
}

fn login_path() -> Result<PathBuf,String> {
    Ok(PathBuf::from(std::env::var_os("HOME").ok_or("Home directory unavailable")?).join("Library/LaunchAgents/app.agentroom.desktop.plist"))
}

#[tauri::command]
fn set_login_start(enabled: bool) -> Result<Value,String> {
    let path=login_path()?;
    if enabled {
        let executable=std::env::current_exe().map_err(|_|"App executable unavailable")?;
        if !executable.to_string_lossy().contains(".app/Contents/MacOS/") {return Err("Install the app bundle before enabling login startup".into());}
        let escaped=executable.to_string_lossy().replace('&',"&amp;").replace('<',"&lt;").replace('>',"&gt;");
        std::fs::create_dir_all(path.parent().unwrap()).map_err(|_|"Unable to create login entry")?;
        let plist=format!("<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict><key>Label</key><string>app.agentroom.desktop</string><key>ProgramArguments</key><array><string>{escaped}</string><string>--background</string></array><key>RunAtLoad</key><true/></dict></plist>");
        std::fs::write(&path,plist).map_err(|_|"Unable to save login entry")?;
    } else if path.exists() {std::fs::remove_file(&path).map_err(|_|"Unable to remove Agent Room login entry")?;}
    Ok(json!({"login_start":enabled}))
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, args, _| { if !args.iter().any(|a|a=="--background") {if let Some(w)=app.get_webview_window("main") {let _=w.show();let _=w.set_focus();}} }))
        .setup(|app| {
            let root = std::env::var_os("AGENT_ROOM_DESKTOP_HOME").map(PathBuf::from).unwrap_or(app.path().app_data_dir()?.parent().unwrap().join("Agent Room"));
            std::fs::create_dir_all(&root)?;
            let binary=std::env::var_os("AGENT_ROOM_HELPER").map(PathBuf::from).unwrap_or(app.path().resource_dir()?.join("helper/agent-room-helper"));
            let child=Arc::new(Mutex::new(Some(launch(&binary,&root)?)));
            let stopping=Arc::new(AtomicBool::new(false));
            let (supervised, stop, home)=(child.clone(),stopping.clone(),root.clone());
            std::thread::spawn(move || { while !stop.load(Ordering::Relaxed) {
                std::thread::sleep(Duration::from_secs(2));
                let mut slot=supervised.lock().unwrap();
                if stop.load(Ordering::Relaxed) { break; }
                let ended=match slot.as_mut() {Some(child)=>child.try_wait().ok().flatten().is_some(),None=>true};
                if ended { *slot=launch(&binary,&home).ok(); }
            }});
            app.manage(Runtime{root,child,stopping});
            if std::env::args().any(|a|a=="--background") {if let Some(w)=app.get_webview_window("main"){let _=w.hide();}}
            Ok(())
        })
        .on_window_event(|window,event| { if let WindowEvent::CloseRequested{api,..}=event {api.prevent_close();let _=window.hide();} })
        .invoke_handler(tauri::generate_handler![control,runtime_info,set_login_start])
        .build(tauri::generate_context!()).expect("Unable to start Agent Room");
    app.run(|app,event| match event {
        tauri::RunEvent::Reopen { .. } => {if let Some(w)=app.get_webview_window("main"){let _=w.show();let _=w.set_focus();}},
        tauri::RunEvent::Exit => {let state=app.state::<Runtime>();state.stopping.store(true,Ordering::Relaxed);if let Some(mut child)=state.child.lock().unwrap().take(){let _=child.kill();let _=child.wait();};},
        _=>{}
    });
}
