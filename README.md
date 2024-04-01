# DallE-Image-Generator
This tool leverages the DallE model via the OpenAI API to generate images in batches. It's designed for users looking to create image datasets for purposes such as concept fine-tuning or style training for AI image models, including Stable Diffusion.

# Usage
Follow these steps to use the DallE-Image-Generator:

1. Navigate to the `settings.ini` file and input your OpenAI API Key.
2. Run `DallEGenerator.py`.
3. Familiarize yourself with the settings on the top/right side of the interface. Hover over each setting for more information, or refer to the detailed settings section below.
4. Enter your image generation prompt. For dynamic prompts, you can incorporate [VARIABLES] within brackets.
5. (Optional) If using [VARIABLES], press the `Analyze Prompt` button. This will introduce a text field for inputting values for each variable. This step is necessary only if your prompt includes variables.
6. (Optional) For each [VARIABLE], provide a list of variable values. Each entry generates one image. Note: Utilizing multiple variables results in the creation of all possible combinations, which can significantly increase the number of generated images. Exercise caution with this feature.
7. Click `Preview Prompt` to review your prompt configuration.
8. Hit the `Generate` button. You will receive an estimate of the cost involved and will be asked to confirm before proceeding.
9. The generated images, along with captions and logs if selected, will be saved in a folder named after today's date. Organization within this folder depends on your chosen settings.

# Settings
**Important Notice:** After modifying settings, you must save your changes using the `[SAVE SETTINGS]` button and restart the program before generating new images. Due to unresolved interface bugs, a program restart is necessary to ensure settings are applied correctly.

**Dataset:** Designates a sub-folder name within the output folder where all images will be stored. If combined with the Caption option, this name will prefix the caption file.

**Caption:** Enables the output of a caption file. If a dataset name is provided, it prefixes the caption. The caption content is derived from the provided prompt or, if `[conceptify]` is enabled, from the concept name.

**Log:** Generates a .log file for each batch of images, containing the prompt and other relevant information.

**Conceptify:** When activated, searches for an additional set of brackets in [VARIABLES] to use as a concise descriptor for organizing images into sub-folders and generating captions accordingly.

**Quantity:** Specifies how many copies of each image to generate. It is recommended not to exceed 9 to avoid excessive generation.

**Model Version:** Select between DallE2 and DallE3 models.

**Quality:** Choose between Standard and HD quality, the latter being available only for DallE3.

**Resolution:** Determines the resolution of the generated images, contingent on the chosen model.

# Examples
The example below illustrates generating 12 images inspired by Batman's style, encompassing variations with an airplane, a bookshelf, and a coffee machine. These images will be organized in a 'BatmanStyle' main folder, with respective sub-folders for each category. A caption file will accompany each category, prefixed with 'BatmanStyle' and the specific category as the caption.

![image](https://github.com/MNeMoNiCuZ/DallE-Image-Generator/assets/60541708/c262c255-4fe7-468a-8ab0-812d3abfc61e)
![image](https://github.com/MNeMoNiCuZ/DallE-Image-Generator/assets/60541708/5d4695f1-913c-4a37-bfda-03f1d541e841)
