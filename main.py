import os
import threading
import time
from datetime import datetime
import subprocess
import requests
import customtkinter as ctk
from tkinter import filedialog, messagebox
from bs4 import BeautifulSoup
import urllib.parse
import shutil
import queue

# Constants
APP_NAME = "Website Copier"
DARK_MODE = "dark"
LIGHT_MODE = "light"
DOWNLOAD_METHODS = {
    "wget": "wget (recommended)",
    "httrack": "HTTrack (advanced)",
    "custom": "Custom (basic)"
}

class WebsiteCopierApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # App configuration
        self.title(APP_NAME)
        self.geometry("800x600")
        self.minsize(700, 500)
        ctk.set_appearance_mode(DARK_MODE)
        ctk.set_default_color_theme("blue")
        
        # Download thread control
        self.download_thread = None
        self.stop_download = False
        self.log_queue = queue.Queue()
        
        # UI Elements
        self.create_widgets()
        
        # Start log monitor
        self.after(100, self.process_log_queue)
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        self.header = ctk.CTkLabel(
            self.main_frame, 
            text=APP_NAME,
            font=("Helvetica", 24, "bold")
        )
        self.header.pack(pady=(10, 20))
        
        # URL Input
        self.url_frame = ctk.CTkFrame(self.main_frame)
        self.url_frame.pack(fill="x", padx=10, pady=5)
        
        self.url_label = ctk.CTkLabel(
            self.url_frame, 
            text="Website URL:",
            font=("Helvetica", 12)
        )
        self.url_label.pack(side="left", padx=(0, 10))
        
        self.url_entry = ctk.CTkEntry(
            self.url_frame,
            placeholder_text="https://example.com",
            width=400
        )
        self.url_entry.pack(side="left", fill="x", expand=True)
        
        # Download Method
        self.method_frame = ctk.CTkFrame(self.main_frame)
        self.method_frame.pack(fill="x", padx=10, pady=5)
        
        self.method_label = ctk.CTkLabel(
            self.method_frame, 
            text="Download Method:",
            font=("Helvetica", 12)
        )
        self.method_label.pack(side="left", padx=(0, 10))
        
        self.method_var = ctk.StringVar(value="wget")
        self.method_menu = ctk.CTkOptionMenu(
            self.method_frame,
            variable=self.method_var,
            values=list(DOWNLOAD_METHODS.values())
        )
        self.method_menu.pack(side="left", fill="x", expand=True)
        
        # Folder Selection
        self.folder_frame = ctk.CTkFrame(self.main_frame)
        self.folder_frame.pack(fill="x", padx=10, pady=5)
        
        self.folder_label = ctk.CTkLabel(
            self.folder_frame, 
            text="Save Location:",
            font=("Helvetica", 12)
        )
        self.folder_label.pack(side="left", padx=(0, 10))
        
        self.folder_entry = ctk.CTkEntry(
            self.folder_frame,
            placeholder_text="Select download folder...",
            width=400
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.folder_button = ctk.CTkButton(
            self.folder_frame,
            text="Browse",
            width=80,
            command=self.select_folder
        )
        self.folder_button.pack(side="left")
        
        # Progress Bar
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=(20, 5))
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame, 
            text="Progress:",
            font=("Helvetica", 12)
        )
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            orientation="horizontal",
            mode="determinate",
            height=20
        )
        self.progress_bar.pack(fill="x", pady=(5, 0))
        self.progress_bar.set(0)
        
        # Log Panel
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        self.log_label = ctk.CTkLabel(
            self.log_frame, 
            text="Download Log:",
            font=("Helvetica", 12)
        )
        self.log_label.pack(anchor="w")
        
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            wrap="word",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Control Buttons
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.start_button = ctk.CTkButton(
            self.button_frame,
            text="Start Download",
            command=self.start_download,
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        )
        self.start_button.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        self.stop_button = ctk.CTkButton(
            self.button_frame,
            text="Stop",
            command=self.stop_download_process,
            fg_color="#c62828",
            hover_color="#b71c1c",
            state="disabled"
        )
        self.stop_button.pack(side="left", fill="x", expand=True)
        
        self.theme_button = ctk.CTkButton(
            self.button_frame,
            text="Toggle Theme",
            command=self.toggle_theme,
            width=120
        )
        self.theme_button.pack(side="right", padx=(10, 0))
    
    def select_folder(self):
        """Open folder selection dialog"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder_path)
    
    def toggle_theme(self):
        """Toggle between dark and light mode"""
        current = ctk.get_appearance_mode()
        new_mode = LIGHT_MODE if current == DARK_MODE else DARK_MODE
        ctk.set_appearance_mode(new_mode)
    
    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_queue.put(formatted_message)
    
    def process_log_queue(self):
        """Process messages from the log queue"""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.insert("end", message)
            self.log_text.see("end")
        self.after(100, self.process_log_queue)
    
    def start_download(self):
        """Start the website download process"""
        url = self.url_entry.get().strip()
        folder = self.folder_entry.get().strip()
        method_key = [k for k, v in DOWNLOAD_METHODS.items() if v == self.method_var.get()][0]
        
        # Validate inputs
        if not url:
            messagebox.showerror("Error", "Please enter a website URL")
            return
        
        if not folder:
            messagebox.showerror("Error", "Please select a download folder")
            return
        
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create folder: {str(e)}")
                return
        
        # Clear previous logs
        self.log_text.delete("1.0", "end")
        
        # Disable start button during download
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        
        # Start download in a separate thread
        self.stop_download = False
        self.download_thread = threading.Thread(
            target=self.download_website,
            args=(url, folder, method_key),
            daemon=True
        )
        self.download_thread.start()
    
    def stop_download_process(self):
        """Stop the ongoing download process"""
        if self.download_thread and self.download_thread.is_alive():
            self.stop_download = True
            self.log_message("Download process stopping...")
            self.stop_button.configure(state="disabled")
    
    def download_website(self, url, folder, method):
        """Download website using the selected method"""
        try:
            if method == "wget":
                self.download_with_wget(url, folder)
            elif method == "httrack":
                self.download_with_httrack(url, folder)
            elif method == "custom":
                self.download_with_custom(url, folder)
            
            if not self.stop_download:
                self.log_message("Download completed successfully!")
                self.progress_bar.set(1)
                self.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    "Website copied successfully!"
                ))
        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            self.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Download failed: {str(e)}"
            ))
        finally:
            self.after(0, self.reset_ui)
    
    def reset_ui(self):
        """Reset UI after download completes or fails"""
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.download_thread = None
    
    def download_with_wget(self, url, folder):
        """Download website using wget"""
        if not shutil.which("wget"):
            raise Exception("wget is not installed or not in PATH")
        
        # Prepare wget command
        cmd = [
            "wget",
            "--mirror",             # Mirror the website
            "--convert-links",      # Convert links for local viewing
            "--adjust-extension",   # Add .html to pages if needed
            "--page-requisites",    # Get all page elements
            "--no-parent",          # Don't ascend to parent directory
            "--random-wait",        # Random wait between requests
            "--limit-rate=1m",      # Limit download rate
            "--no-clobber",         # Don't overwrite existing files
            "--directory-prefix", folder,
            url
        ]
        
        self.log_message(f"Starting download with wget: {' '.join(cmd)}")
        
        # Run wget in a subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        while True:
            if self.stop_download:
                process.terminate()
                self.log_message("Download stopped by user")
                break
            
            output = process.stdout.readline()
            if output:
                self.log_message(output.strip())
            
            return_code = process.poll()
            if return_code is not None:
                if return_code != 0:
                    raise Exception(f"wget failed with return code {return_code}")
                break
            
            time.sleep(0.1)
    
    def download_with_httrack(self, url, folder):
        """Download website using HTTrack"""
        if not shutil.which("httrack"):
            raise Exception("HTTrack is not installed or not in PATH")
        
        # Prepare HTTrack command
        project_name = urllib.parse.urlparse(url).netloc or "website"
        project_path = os.path.join(folder, project_name)
        
        cmd = [
            "httrack",
            url,
            "-O", project_path,
            "--mirror",
            "--update",             # Continue interrupted download
            "--robots=0",           # Ignore robots.txt
            "--connection-per-second=2",  # Limit requests
            "--max-rate=1000000",   # Limit download rate (1MB/s)
            "--disable-security-limits"  # Bypass some limits
        ]
        
        self.log_message(f"Starting download with HTTrack: {' '.join(cmd)}")
        
        # Run HTTrack in a subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        while True:
            if self.stop_download:
                process.terminate()
                self.log_message("Download stopped by user")
                break
            
            output = process.stdout.readline()
            if output:
                self.log_message(output.strip())
                # Extract progress from output if possible
                if "%" in output:
                    try:
                        percent = float(output.split("%")[0].split()[-1])
                        self.progress_bar.set(percent / 100)
                    except:
                        pass
            
            return_code = process.poll()
            if return_code is not None:
                if return_code != 0:
                    raise Exception(f"HTTrack failed with return code {return_code}")
                break
            
            time.sleep(0.1)
    
    def download_with_custom(self, url, folder):
        """Custom download using requests and BeautifulSoup"""
        self.log_message("Starting custom download (this may take a while for large sites)")
        
        try:
            # Create base directory
            domain = urllib.parse.urlparse(url).netloc
            base_dir = os.path.join(folder, domain)
            os.makedirs(base_dir, exist_ok=True)
            
            # Download homepage first
            self.download_page(url, base_dir, base_url=url)
            
            # TODO: Implement recursive download of all links
            # This is a simplified version - a complete implementation would need
            # to handle relative links, assets, and recursive downloading
            
            self.log_message("Basic download complete (note: custom method may not get all assets)")
        except Exception as e:
            raise Exception(f"Custom download failed: {str(e)}")
    
    def download_page(self, page_url, save_dir, base_url):
        """Download a single page and its assets"""
        try:
            response = requests.get(page_url, timeout=10)
            response.raise_for_status()
            
            # Determine save path
            parsed_url = urllib.parse.urlparse(page_url)
            path = parsed_url.path.lstrip("/")
            if not path:
                path = "index.html"
            elif not os.path.splitext(path)[1]:
                path = os.path.join(path, "index.html")
            
            save_path = os.path.join(save_dir, path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Save the content
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            self.log_message(f"Downloaded: {page_url}")
            
            # Update progress (very rough estimation)
            self.progress_bar.set(min(self.progress_bar.get() + 0.01, 0.99))
            
            return response.text
        except Exception as e:
            self.log_message(f"Failed to download {page_url}: {str(e)}")
            return None

if __name__ == "__main__":
    app = WebsiteCopierApp()
    app.mainloop()