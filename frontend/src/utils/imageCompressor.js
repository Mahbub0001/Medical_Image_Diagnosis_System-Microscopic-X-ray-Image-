/**
 * imageCompressor.js
 * Client-side image compression using HTML5 Canvas API.
 *
 * Compresses images BEFORE sending to backend to prevent OOM crashes
 * on Render's free tier (512MB RAM limit).
 *
 * Strategy:
 *  - Max dimension: 1024px (width or height, whichever is larger)
 *  - Output quality: 0.85 (85%) JPEG
 *  - Always converts to JPEG (removes alpha channel safely)
 *  - Returns a File object (drop-in replacement for the original File)
 */

const MAX_DIMENSION = 1024; // px
const JPEG_QUALITY = 0.85;  // 85%

/**
 * Compresses an image File using Canvas.
 *
 * @param {File} file - The original image file from the input element.
 * @returns {Promise<File>} - A new compressed File object ready for FormData.
 */
export function compressImage(file) {
  return new Promise((resolve, reject) => {
    // If the file is already small enough (< 200KB), skip compression
    if (file.size < 200 * 1024) {
      resolve(file);
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        // Calculate new dimensions while preserving aspect ratio
        let { width, height } = img;

        if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
          if (width >= height) {
            height = Math.round((height / width) * MAX_DIMENSION);
            width = MAX_DIMENSION;
          } else {
            width = Math.round((width / height) * MAX_DIMENSION);
            height = MAX_DIMENSION;
          }
        }

        // Draw onto canvas at the new dimensions
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        // Fill with white background first (handles RGBA → RGB conversion)
        ctx.fillStyle = "#FFFFFF";
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0, width, height);

        // Convert to Blob (JPEG for best compression)
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Canvas toBlob failed"));
              return;
            }
            // Create a new File from the blob, preserving the original filename
            const compressedFile = new File(
              [blob],
              file.name.replace(/\.(png|jpeg|jpg)$/i, ".jpg"),
              { type: "image/jpeg", lastModified: Date.now() }
            );
            resolve(compressedFile);
          },
          "image/jpeg",
          JPEG_QUALITY
        );
      };

      img.onerror = () => reject(new Error("Failed to load image for compression"));
      img.src = event.target.result;
    };

    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}
