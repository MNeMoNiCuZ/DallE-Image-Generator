import subprocess
import sys
import pkg_resources
import tkinter as tk
from tkinter import scrolledtext, Canvas, Scrollbar, Frame, simpledialog, messagebox
from itertools import product
import re
import openai
import os
import hashlib
import threading
import time
from configparser import ConfigParser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.exceptions import HTTPError, Timeout, RequestException
import traceback

# Function to check the version of the openai package
def check_openai_version(required_version='1.2.0'):  # Ensure this matches the versioning style of the package
    actual_version = pkg_resources.get_distribution("openai").version
    if pkg_resources.parse_version(actual_version) < pkg_resources.parse_version(required_version):
        raise ImportError(f"Your openai package version is {actual_version}, but version {required_version} or higher is required.")
    else:
        print(f"openai package version is {actual_version}.")

# Call the version check function
check_openai_version()
# Function to load settings from the settings.ini file
def load_settings():
    config = ConfigParser()
    config.read('settings.ini')
    return {
        'api_key': config['openai']['api_key'],
        'model_version': config['defaults'].get('model_version', 'DALLE3'),
        'model_mode': config['defaults'].get('model_mode', 'standard'),
        'size': config['defaults'].get('size', '1024x1024'),
        'generate_caption': config['defaults'].getboolean('generate_caption', True),
        'generate_log': config['defaults'].getboolean('generate_log', True),
        'conceptify': config['defaults'].getboolean('conceptify', False),
        'dataset': config['defaults'].get('dataset', ''),
        'quantity': config['defaults'].getint('quantity', 1),
        'prompt': config['defaults'].get('prompt', '')
    }

# Load settings
settings = load_settings()
openai.api_key = settings['api_key']

# Initialize the main application window
root = tk.Tk()
root.title("DALL·E Dataset Generator")
root.geometry("1100x750")  # Set the initial size of the window
text_font = ('Arial', 12)  # Define a font for better readability

# Create Tkinter variables after the root window is created
generate_caption_var = tk.BooleanVar(value=settings['generate_caption'])
generate_log_var = tk.BooleanVar(value=settings['generate_log'])
conceptify_var = tk.BooleanVar(value=settings['conceptify'])
dataset_var = tk.StringVar(value=settings['dataset'])
model_version_var = tk.StringVar(value=settings['model_version'])
model_mode_var = tk.StringVar(value=settings['model_mode'])
size_var = tk.StringVar(value=settings['size'])
quantity_var = tk.StringVar(value=str(settings['quantity']))

# Pricing information
PRICING = {
    'DALLE3': {
        '1024×1024': 0.040,
        '1024×1792': 0.080,
        '1792×1024': 0.080,
    },
    'DALLE3HD': {
        '1024×1024': 0.080,
        '1024×1792': 0.120,
        '1792×1024': 0.120,
    },
    'DALLE2': {
        '1024×1024': 0.020,
        '512×512': 0.018,
        '256×256': 0.016,
    }
}

# Function to create a tooltip
class CreateToolTip(object):
    def __init__(self, widget, text):
        self.wait_time = 500     #milliseconds
        self.wrap_length = 350   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.id = None
        self.tw = None

    def on_enter(self, event=None):
        self.schedule()

    def on_leave(self, event=None):
        self.unschedule()
        self.hide_tooltip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.wait_time, self.show_tooltip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def show_tooltip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wrap_length)
        label.pack(ipadx=1)

    def hide_tooltip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

# Create a canvas and a scrollbar
canvas = Canvas(root)
scrollbar = Scrollbar(root, command=canvas.yview)
scrollable_frame = Frame(canvas)

# Pack the scrollbar and configure the canvas
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
canvas.configure(yscrollcommand=scrollbar.set)

# Add the frame to the canvas
canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')

# Final output text box setup with title and scrollbar
final_prompt_label = tk.Label(scrollable_frame, text="Final Prompt", font=text_font)
preview_text = scrolledtext.ScrolledText(scrollable_frame, width=70, height=10, font=text_font)

# Function to update the canvas frame width when the canvas is resized
def on_canvas_configure(event):
    canvas.itemconfig(canvas_frame, width=event.width)

canvas.bind("<Configure>", on_canvas_configure)

# Bind the scrollable_frame to the size of the canvas.
def on_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

scrollable_frame.bind("<Configure>", on_frame_configure)

# Dictionary to hold the variable text areas
variable_text_areas = {}

# Function to calculate the cost of generating images
def calculate_cost(model_version, resolution, quality, quantity):
    # Convert the resolution format for correct dictionary lookup
    resolution_key = resolution.replace('x', '×')

    # Determine the pricing category based on quality and model version
    pricing_category = model_version
    if quality == 'hd' and model_version == "DALLE3":
        pricing_category = 'DALLE3HD'

    # Look up the price based on resolution and pricing category
    price_per_image = PRICING.get(pricing_category, {}).get(resolution_key, 0.0)
    total_cost = price_per_image * quantity
    return total_cost

# Function to analyze the prompt and create input fields for variables
def analyze_prompt():
    # Extract the variables from the prompt
    prompt = prompt_text.get("1.0", tk.END)
    new_variables = re.findall(r'\[(.*?)\]', prompt)

    # Get current variables and their text
    current_text = {var: variable_text_areas[var]['text_area'].get("1.0", tk.END)
                    for var in variable_text_areas}

    # Clear the dictionary since we are rebuilding the UI
    variable_text_areas.clear()

    # Remove the variable_frame and recreate it to ensure all children are removed
    global variable_frame
    variable_frame.destroy()
    variable_frame = tk.Frame(scrollable_frame)
    variable_frame.pack(fill=tk.BOTH, expand=True)

    # Create text input fields for new variables
    for var in new_variables:
        label = tk.Label(variable_frame, text=f"[{var}]", font=text_font)
        label.pack()
        text_area = scrolledtext.ScrolledText(variable_frame, width=70, height=5, font=text_font)
        text_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        # If this variable was already present, insert the previous text
        if var in current_text:
            text_area.insert("1.0", current_text[var])
        variable_text_areas[var] = {'text_area': text_area, 'label': label}

    # Repack the Final Prompt label and text area to ensure they stay at the bottom
    final_prompt_label.pack_forget()
    preview_text.pack_forget()
    final_prompt_label.pack()
    preview_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Print completion of text area creation
    print("Text input fields updated.")

# Function to preview the prompts with all permutations of variables
def preview_prompts():
    # Extract the base prompt
    base_prompt = prompt_text.get("1.0", tk.END).strip()

    # Collect all the variable inputs
    variables = {}
    for var, widgets in variable_text_areas.items():
        text_area = widgets['text_area']
        entries = [entry.strip() for entry in text_area.get("1.0", tk.END).split('\n') if entry.strip()]
        variables[var] = entries

    # Generate all permutations of the variables
    keys, values = zip(*variables.items()) if variables else ([], [])
    permutations = [dict(zip(keys, v)) for v in product(*values)]

    # Clear the preview field
    preview_text.delete("1.0", tk.END)

    # Generate and display the previews
    for perm in permutations:
        permuted_prompt = base_prompt
        for var, val in perm.items():
            permuted_prompt = permuted_prompt.replace(f'[{var}]', val)
        preview_text.insert(tk.END, permuted_prompt + '\n')

# Function to confirm image generation with cost
def confirm_generation():
    total_images = len(preview_text.get("1.0", tk.END).strip().split('\n')) * int(quantity_entry.get())
    total_cost = calculate_cost(model_version_var.get(), resolution_var.get(), quality_var.get(), total_images)
    
    # Format the message to include the cost
    confirmation_message = f"You are about to generate {total_images} images.\n" \
                           f"This will cost approximately ${total_cost:.2f}.\n" \
                           f"Do you wish to proceed?"
    
    response = messagebox.askyesno("Generate Images", confirmation_message)
    if response:
        threading.Thread(target=generate_images, daemon=True).start()
        
# Function to preview the requests
def preview_requests():
    prompts = preview_text.get("1.0", tk.END).strip().split('\n')
    size = resolution_var.get()
    quality = quality_var.get()
    model_version = model_version_var.get()

    for prompt in prompts:
        params = {
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality
        }
        if model_version == "DALLE3":
            params["model"] = "dall-e-3"
        elif model_version == "DALLE2":
            params["model"] = "dall-e-2"
        
        print(f"Request Preview: {params}")

# Function to generate images in parallel
def generate_images():
    prompts = preview_text.get("1.0", tk.END).strip().split('\n')
    quantity = int(quantity_entry.get())
    size = resolution_var.get()
    quality = quality_var.get()
    generate_log = generate_log_var.get()
    generate_caption = generate_caption_var.get()
    conceptify = conceptify_var.get()
    dataset = dataset_var.get()

    # Filter out empty prompts
    prompts = [prompt for prompt in prompts if prompt]

    # If there are no valid prompts, show a warning
    if not prompts:
        messagebox.showwarning("Warning", "No valid prompts were provided. Please enter at least one prompt and press 'Preview Prompts' before generating images.")
        return

    # Generate images one by one
    for prompt in prompts:
        for _ in range(quantity):
            create_images_thread(prompt, 1, size, quality, model_version_var.get(), generate_log, generate_caption, conceptify, dataset)
            time.sleep(1)            

    print("All images have been processed.")

# Helper function to create images
def create_images_thread(prompt, n, size, quality, model_version, generate_log, generate_caption, conceptify, dataset):
    
    # Call create_image with all the required parameters, including conceptify
    image_urls, concept = create_image(prompt, n=n, size=size, quality=quality, conceptify=conceptify)
    
    if image_urls:  # Check if the image_urls list is not empty
        for url in image_urls:
            # Pass the actual boolean values and the concept to the function
            save_image_details_and_download(url, prompt, generate_log, generate_caption, concept, dataset)
            print(f"Generated image for prompt: '{prompt}' with URL: {url}")
    else:
        print(f"No images were generated for prompt: '{prompt}'. Please check for errors.")
    
    # Separator for end of the request
    print("-"*80 + "\n")

    
# Function to create an image with DALL·E
def create_image(prompt, n=1, model="dall-e-3", size="1024x1024", quality="standard", conceptify=False):
    concept = None  # Initialize concept as None
    try:
        print("-" * 80 + "\n")
        print(f"Prompt before processing: {prompt}")  # Debug print: Print the prompt before removing concept
        print(f"Size: {size}")  # Debug print: Print the size
        print(f"Quality: {quality}")  # Debug print: Print the quality

        # Extract concept if conceptify is enabled
        if conceptify:
            match = re.search(r"\[(.*?)\](.*)", prompt, re.VERBOSE)
            if match:
                concept = match.group(1)  # The concept inside the square brackets
                prompt = match.group(2).strip()  # The rest of the prompt without the concept
                print(f"Concept identified: {concept}")  # Debug print: Print the identified concept
                print(f"Prompt after processing: {prompt}")  # Debug print: Print the prompt after removing concept
            else:
                print("No concept identified: Regex did not match. Prompt was: " + repr(prompt))
        else:
            print("Conceptify is disabled.")
        print("-" * 80 + "\n")

        # Prepare the parameters for the API call
        params = {
            "prompt": prompt,
            "n": n,
            "size": size,
            "model": model,
            "quality": quality
        }

        # Print the parameters to the console for debugging
        print(f"Making API request with params: {params}")

        # Create an OpenAI client instance
        client = openai.OpenAI(api_key=settings['api_key'])

        # Make an API call to OpenAI's Image creation endpoint with the parameters
        response = client.images.generate(**params)
        print(f"API Response: {response}")

        # Extract the image URLs from the response
        image_urls = [image.url for image in response.data]
        return image_urls, concept  # Return both the image URLs and the concept

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()

    # This return should be outside the try...except block
    return [], None  # Return an empty list and None for concept if an error occurred


# Function to save the image URL to a text file, download the image, and optionally generate a caption file
def save_image_details_and_download(image_url, prompt, generate_log, generate_caption, concept, dataset):
    # Get the current datetime for timestamping
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    base_directory = date_str
    # Check if 'dataset' has a truthy value (non-empty string) before adding it to the path
    if dataset and dataset.strip():
        base_directory = os.path.join(base_directory, dataset.strip())
    if concept:
        base_directory = os.path.join(base_directory, concept)

    # Create the directory if it does not exist
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)

    # Print the intended save path for the log
    print(f"Intended save path: {os.path.abspath(base_directory)}")

    # Create a hash of the image URL for a unique filename
    hash_object = hashlib.md5(image_url.encode())
    hash_hex = hash_object.hexdigest()

    # Define the filename prefix with dataset and concept if available
    file_prefix = ""
    if dataset:
        file_prefix += f"{dataset} - "
    if concept:
        file_prefix += f"{concept} - "

    # Define the filenames for the log file, the image file, and the caption file
    formatted_time_str = now.strftime("%Y-%m-%d - %H.%M.%S")
    log_filename = f"{file_prefix}{formatted_time_str} - {hash_hex}.log"
    image_filename = f"{file_prefix}{formatted_time_str} - {hash_hex}.png"
    caption_filename = f"{file_prefix}{formatted_time_str} - {hash_hex}.txt"

    # Save the log file if "Generate Log" is checked
    if generate_log:
        with open(os.path.join(base_directory, log_filename), 'w') as file:
            file.write(f"Prompt: {prompt}\n")
            file.write(f"Image URL: {image_url}\n")
            file.write(f"Timestamp: {now}\n")

    print(f"Generate Caption: {generate_caption}")
    # Save the caption file if "Generate Caption" is checked
    if generate_caption:
        # Always remove the concept and surrounding brackets from the prompt first
        concept_with_brackets = f"[{concept}]" if concept else ""
        prompt_without_concept = prompt.replace(concept_with_brackets, '').strip()

        # Check the state of the conceptify variable and prepare the caption content accordingly
        if conceptify_var.get() and concept:
            # If conceptify is true, use only the concept
            caption_content = concept
        else:
            # If conceptify is false, use the modified prompt without the concept
            caption_content = prompt_without_concept

        # Print the state of conceptify_var
        print(f"State of conceptify_var: {conceptify_var.get()}")

        # If the dataset is provided, prepend it to the caption content
        if dataset:
            caption_content = f"{dataset} {caption_content}".strip()

        # Print the final caption content
        print(f"Final caption content: {caption_content}")

        # Write the caption content to the file
        with open(os.path.join(base_directory, caption_filename), 'w') as file:
            file.write(caption_content)

        # Save the caption file if "Generate Caption" is checked
        if generate_caption:
            # Always remove the concept and surrounding brackets from the prompt first
            concept_with_brackets = f"[{concept}]" if concept else ""
            prompt_without_concept = prompt.replace(concept_with_brackets, '').strip()

            # Check the state of the conceptify variable and prepare the caption content accordingly
            if conceptify_var.get() and concept:
                # If conceptify is true, use only the concept
                caption_content = concept
            else:
                # If conceptify is false, use the modified prompt without the concept
                caption_content = prompt_without_concept

            # If the dataset is provided, prepend it to the caption content
            if dataset:
                caption_content = f"{dataset} {caption_content}".strip()

            # Write the caption content to the file
            with open(os.path.join(base_directory, caption_filename), 'w') as file:
                file.write(caption_content)

    # Download the image and save it to the appropriate directory
    try:
        response = requests.get(image_url, timeout=10)  # Timeout in seconds
        if response.status_code == 200:
            with open(os.path.join(base_directory, image_filename), 'wb') as file:
                file.write(response.content)
        else:
            print(f"Failed to download the image. Status code: {response.status_code}")
    except requests.Timeout:
        print(f"Request timed out for URL: {image_url}")
    except requests.RequestException as e:
        print(f"An error occurred: {e}")


# Function to update resolution options and quality menu based on model version
def update_options_based_on_model(*args):
    # Clear the existing menu entries
    resolution_menu['menu'].delete(0, 'end')

    # Update the resolution menu based on the model version
    if model_version_var.get() == 'DALLE2':
        # Add the DALL-E 2 resolutions
        new_resolutions = ["1024x1024", "512x512", "256x256"]
        quality_menu.pack_forget()  # Hide the quality menu for DALL-E 2
    else:
        # Add the DALL-E 3 resolutions
        new_resolutions = ["1024x1024", "1024x1792", "1792x1024"]
        quality_menu.pack(side=tk.LEFT, padx=(0, 20), pady=0)  # Show the quality menu for DALL-E 3
        resolution_menu.pack(side=tk.LEFT, padx=(20, 20), pady=0)

    # Add new resolutions to the resolution menu
    for resolution in new_resolutions:
        resolution_menu['menu'].add_command(label=resolution, command=tk._setit(resolution_var, resolution))

    # Set the default resolution
    resolution_var.set(new_resolutions[0])

# Save Settings-button
def save_settings():
    config = ConfigParser()
    config['openai'] = {'api_key': openai.api_key}
    config['defaults'] = {
        'model_version': model_version_var.get(),
        'model_mode': quality_var.get(),  # Assuming you have renamed model_mode_var to quality_var
        'size': resolution_var.get(),
        'generate_caption': generate_caption_var.get(),
        'generate_log': generate_log_var.get(),
        'conceptify': conceptify_var.get(),
        'dataset': dataset_entry.get(),
        'quantity': str(quantity_entry.get()),  # Make sure to use quantity_entry if that's your input field
        'prompt': prompt_text.get("1.0", tk.END).strip()  # Strip to remove any trailing newlines
    }
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)
    messagebox.showinfo("Settings", "Settings saved successfully.")

#GUI
# Button frame setup
button_frame = tk.Frame(scrollable_frame)
button_frame.pack(fill=tk.X)

analyze_button = tk.Button(button_frame, text="Analyze Prompt", padx=20, pady=20, command=analyze_prompt)
analyze_button.pack(side=tk.LEFT, padx=5, pady=5)

preview_button = tk.Button(button_frame, text="Preview Prompts", padx=20, pady=20, command=preview_prompts)
preview_button.pack(side=tk.LEFT, padx=5, pady=5)

generate_button = tk.Button(button_frame, text="Generate", padx=20, pady=20, command=confirm_generation)
generate_button.pack(side=tk.LEFT, padx=5, pady=5)

save_settings_button = tk.Button(button_frame, text="Save Settings", padx=20, pady=20, command=save_settings)
save_settings_button.pack(side=tk.LEFT, padx=5, pady=5)

# Apply tooltips to the buttons
CreateToolTip(analyze_button, "Click to analyze the prompt in the (Original Workplace). If you have one or more words encapsulated in [], each such word will get it's own variable field below. Fill these fields in with the different variations you wish to generate.")
CreateToolTip(preview_button, "Click to preview the prompts in the Resulting Prompt section.")
CreateToolTip(generate_button, "Click to start generating images based on the prompt. You will be asked to confirm after pressing.")
CreateToolTip(save_settings_button, "Click to save the current settings. WARNING! You must restart the program if you change the Dataset or other settings before generating. To be fixed.")

# Update the button command to use the new generate_images function
generate_button.config(command=confirm_generation)

# Frame for resolution
top_frame = tk.Frame(button_frame)
top_frame.pack(side=tk.TOP, fill=tk.X, expand=True, pady=0)

# Label for the dataset entry field
dataset_label = tk.Label(top_frame, text="Dataset:")
dataset_label.pack(side=tk.LEFT, padx=(0, 5), pady=0)
dataset_entry = tk.Entry(top_frame, width=20)
dataset_entry.pack(side=tk.LEFT, padx=(0, 5), pady=0)
dataset_entry.insert(0, str(settings['dataset']))
CreateToolTip(dataset_entry, "Enter a name to categorize your generated images under a specific dataset. This will organize the images in the output folder, as well as be used in captions if enabled. WARNING! You must restart the program if you change the Dataset or other settings before generating. To be fixed.")

# Model Version input field with label and drop-down
model_version_options = ["DALLE2", "DALLE3"]
model_version_var = tk.StringVar(root)
model_version_var.set(model_version_options[1]) 
model_version_var.trace('w', update_options_based_on_model)  # Bind the update function to model version changes
model_version_menu = tk.OptionMenu(top_frame, model_version_var, *model_version_options, command=update_options_based_on_model)
model_version_menu.pack(side=tk.LEFT, padx=(0, 5), pady=0)
model_version_var.trace_add('write', update_options_based_on_model)
CreateToolTip(model_version_menu, "Select the model version for generating images.")

# Quality menu created but not packed, will be updated dynamically
quality_options = ["standard", "hd"]
quality_var = tk.StringVar(root)
quality_var.set(quality_options[0]) 
quality_menu = tk.OptionMenu(top_frame, quality_var, *quality_options)
quality_menu.pack(side=tk.LEFT, padx=(0, 5), pady=0)
CreateToolTip(quality_menu, "Choose the quality level for the generated images.")

# Resolution menu created but not packed, will be updated dynamically
resolution_options = []
resolution_var = tk.StringVar(root)
resolution_var.set(resolution_options[0]) if resolution_options else ""  # Set the default option if available
resolution_menu = tk.OptionMenu(top_frame, resolution_var, "")
resolution_menu.pack(side=tk.LEFT, padx=(0, 5), pady=0)
CreateToolTip(resolution_menu, "Select the resolution for the generated images.")

# Frame for image quantity
bottom_frame = tk.Frame(button_frame)
bottom_frame.pack(side=tk.TOP, fill=tk.X, expand=True, pady=0)

# Insert checkboxes here
generate_caption_checkbox = tk.Checkbutton(bottom_frame, text="Caption", variable=generate_caption_var)
generate_caption_checkbox.pack(side=tk.LEFT, padx=(0, 5))
CreateToolTip(generate_caption_checkbox, "Check to generate captions for each image. If you have a Dataset specified, this will be used for the captions too.")

generate_log_checkbox = tk.Checkbutton(bottom_frame, text="Log", variable=generate_log_var)
generate_log_checkbox.pack(side=tk.LEFT, padx=(0, 5))
CreateToolTip(generate_log_checkbox, "Generates a log file for the generation. Contains prompt info and a few more bits.")

conceptify_checkbox = tk.Checkbutton(bottom_frame, text="Conceptify", variable=conceptify_var)
conceptify_checkbox.pack(side=tk.LEFT, padx=(0, 5))
CreateToolTip(conceptify_checkbox, "If true, it will look for a word encapsulated in [] in your variable. This will stripped out of the prompt, and used as the name for both file names and captions.")

# Image Quantity input field
quantity_entry = tk.Entry(bottom_frame, width=5)
quantity_entry.pack(side=tk.LEFT, padx=(0, 5), pady=0)
quantity_entry.insert(0, str(settings['quantity']))
tk.Label(bottom_frame, text=" Quantity").pack(side=tk.LEFT, padx=(0, 5), pady=0)
CreateToolTip(quantity_entry, "The number of images to generate. Keep it below 10.")

# Prompt text box setup with title and scrollbar
tk.Label(scrollable_frame, text="Original Prompt", font=text_font).pack()
prompt_text = scrolledtext.ScrolledText(scrollable_frame, width=70, height=10, font=text_font)
prompt_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
prompt_text.insert("1.0", settings['prompt'])

# Frame for the variable input fields
variable_frame = tk.Frame(scrollable_frame)
variable_frame.pack(fill=tk.BOTH, expand=True)

# Final output text box setup with title and scrollbar
final_prompt_label = tk.Label(scrollable_frame, text="Resulting Prompt", font=text_font)
final_prompt_label.pack()
preview_text = scrolledtext.ScrolledText(scrollable_frame, width=70, height=10, font=text_font)
preview_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

# Initialize the options based on the current model version
update_options_based_on_model()

# Update UI elements based on settings
model_version_var.set(settings['model_version'])
quality_var.set(settings['model_mode'])
resolution_var.set(settings['size'])
generate_caption_var.set(settings['generate_caption'])
generate_log_var.set(settings['generate_log'])
conceptify_var.set(settings['conceptify'])
dataset_entry.delete(0, tk.END)
dataset_entry.insert(0, settings['dataset'])
quantity_entry.delete(0, tk.END)
quantity_entry.insert(0, str(settings['quantity']))
prompt_text.delete("1.0", tk.END)
prompt_text.insert("1.0", settings['prompt'])

# Run the main application loop
root.mainloop()
