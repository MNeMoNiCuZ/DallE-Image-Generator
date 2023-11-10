# DallE-Image-Generator
An image generator using DallE and the OpenAI API to create batches of images.

It could be useful to batch-generate image datasets for concept finetuning or style training for AI image models like Stable Diffusion.

# Usage
1. Open the settings.ini and add your OpenAI API Key.
2. Launch DallEGenerator.py
3. Look at the settings on the top/right side. There's mouse-over information, or see the section below.
4. Edit the prompt. Optional: You can use brackets as [VARIABLES].
5. Optional: Press the Analyze Prompt-button. It will add a text-field for any [VARIABLES] you added. You only need to do this if you are using [VARIABLES].
6. Optional: Fill in the list of variables for each of your [VARIABLES]. Each line you add here will generate 1 image. If you use multiple variables, the script will make all possible combinations. Use with caution!
7. Press the Preview Prompt-button.
8. Press the Generate-button. You will be told the cost of generation and asked to proceed.
9. Images should be output to a folder with today's date, and the images/captions/logs will be output based on the settings.

# Settings
**WARNING: If you change settings, you should press the [SAVE SETTINGS]-button, and then restart the program before generating again. There are some interface bugs I haven't fixed so it needs to refresh like this for now.**

**Dataset**: If you have a dataset in the field, all images will be placed inside a sub-folder with this name. If used with the Caption setting, the dataset will be added as a prefix to the caption-file.

**Caption**: If you want to output a caption file. If you have a dataset name, this will be used as a prefix. The caption will either use the prompt that you provided, or if you used the [conceptify] option, it will be the concept.

**Log**: Outputs a .log-file for each generation. It contains the prompt and some other information.

**Conceptify**: If enabled, the script will look for an additional layer of [brackets] in your [VARIABLES]. This additional brackets is meant to be a shorter version of your variable, which will be used to place images in a folder based on the name of it. For example: If you enter "[plane] an airplane in the skies" for one of your variables, this image will be generated in a "plane"-subfolder, and the word "plane" will be used as the caption, but the image prompt will use "an airplane in the skies".

**Quantity**: The number of copies of each image to generate. Do not use values of 10 or higher.

**Model Version**: DallE2 or DallE3.

**Quality**: Standard or HD (only for DallE3).

**Resolution**: Based on the model.

# Examples
![image](https://github.com/MNeMoNiCuZ/DallE-Image-Generator/assets/60541708/c262c255-4fe7-468a-8ab0-812d3abfc61e)
This would generate 12 images in a Batman-like style. 4x with an airplane, 4x with a bookshelf, and 4x with a coffee machine, all in the style of Batman. All generations would be placed in a folder called BatmanStyle, and there would be a subfolder for airplane, bookshelf and coffee machine. It will also output a .txt caption file with the BatmanStyle as prefix, and airplane/bookshelf/coffee machine as the caption.
![image](https://github.com/MNeMoNiCuZ/DallE-Image-Generator/assets/60541708/5d4695f1-913c-4a37-bfda-03f1d541e841)
