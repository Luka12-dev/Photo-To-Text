use std::env;
use std::process::{Command, Stdio};
use std::io::{self, Read};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: ocr_rs <image>");
        std::process::exit(2);
    }
    let image = &args[1];

    // call tesseract CLI - ensure tesseract is installed
    let mut child = Command::new("tesseract")
        .arg(image)
        .arg("stdout")
        .arg("-l")
        .arg("eng")
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to spawn tesseract");

    let mut out = String::new();
    if let Some(mut s) = child.stdout.take() {
        s.read_to_string(&mut out).unwrap_or(0);
    }
    let status = child.wait().expect("failed to wait on tesseract");
    if !status.success() {
        eprintln!("tesseract failed");
        std::process::exit(3);
    }
    print!("{}", out);
}