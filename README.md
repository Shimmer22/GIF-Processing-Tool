# GIF Processing Tool

A web-based tool for processing and manipulating GIF files. This application allows users to upload GIFs, perform various transformations, and download the results.

## Features

-   **Resize:** Resizes all uploaded GIFs to a standard 240x240 pixel format.
-   **Auto-Split:** Automatically splits GIFs with a 2:1 aspect ratio (e.g., 480x240) into two separate, square GIFs.
-   **Duration Calculation:** Calculates the total animation duration and suggests a descriptive filename (e.g., `happy_1_5s.gif`).
-   **Custom Filename:** Allows users to edit the suggested filename before downloading.
-   **Flip:** Horizontally flips the GIF. This action can be toggled.
-   **RGB Channel Swap:** Allows swapping the Red, Green, and Blue color channels to create interesting visual effects.

## Requirements

-   Python 3.x
-   The libraries listed in the `requirements.txt` file.

## How to Run

1.  **Install Dependencies:**
    Open your terminal or command prompt and run the following command to install the necessary Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start the Server:**
    In the same directory, run the application using `uvicorn`:
    ```bash
    python app.py
    ```

3.  **Access the Tool:**
    Open your web browser and navigate to `http://127.0.0.1:8000`.

## How to Use

1.  **Upload:** Drag and drop a GIF file onto the upload area, or click the box to open a file selector.
2.  **Process:** The tool will automatically process the GIF. The resulting preview(s) will appear below the upload box.
3.  **Manipulate:**
    -   Use the **"左右翻转" (Flip)** button to mirror the GIF horizontally.
    -   Select a new color mapping from the dropdown (e.g., GBR) and click **"交换通道" (Swap Channels)** to change the colors.
    -   Edit the filename in the text box provided in the preview card.
4.  **Download:** Click the **"下载" (Download)** button to save the final GIF to your computer.

---

*This project was developed with the assistance of Gemini, a large language model from Google.*

---

# GIF 处理工具

一个用于处理和操作GIF文件的网页工具。该应用允许用户上传GIF，执行多种转换，并下载处理结果。

## 功能

-   **调整尺寸:** 将所有上传的GIF尺寸统一调整为240x240像素。
-   **自动分割:** 自动将宽高比为2:1的GIF（例如480x240）分割成两个独立的方形GIF。
-   **计算时长:** 计算动画的总持续时间，并生成一个描述性的建议文件名（例如 `happy_1_5s.gif`）。
-   **自定义文件名:** 允许用户在下载前编辑建议的文件名。
-   **翻转:** 水平翻转GIF。此操作可反复点击以切换状态。
-   **RGB通道交换:** 允许交换红、绿、蓝颜色通道，以创造有趣的视觉效果。

## 环境要求

-   Python 3.x
-   `requirements.txt` 文件中列出的所有Python库。

## 如何运行

1.  **安装依赖:**
    打开你的终端或命令提示符，运行以下命令来安装所需的Python库：
    ```bash
    pip install -r requirements.txt
    ```

2.  **启动服务:**
    在项目目录下，使用 `uvicorn` 运行应用：
    ```bash
    python app.py
    ```

3.  **访问工具:**
    打开你的网页浏览器并访问 `http://127.0.0.1:8000`。

## 如何使用

1.  **上传:** 将一个GIF文件拖拽到上传区域，或者点击该区域以打开文件选择器。
2.  **处理:** 工具会自动处理GIF，处理后的预览图会显示在上传框下方。
3.  **操作:**
    -   点击 **"左右翻转"** 按钮来水平镜像GIF。
    -   从下拉菜单中选择一个新的颜色映射（例如 GBR），然后点击 **"交换通道"** 来改变颜色。
    -   在预览卡片提供的文本框中编辑你想要的文件名。
4.  **下载:** 点击 **"下载"** 按钮，将最终的GIF保存到你的电脑上。

---

*本项目由Google的大型语言模型Gemini协助开发。*
