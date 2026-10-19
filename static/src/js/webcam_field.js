/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { useRef, useState } from "@odoo/owl";

/**
 * Widget "adk_webcam" : étend le champ Image standard d'Odoo en ajoutant un
 * bouton "Prendre une photo (webcam)". Utilise l'API navigator.mediaDevices
 * pour capturer une image et la convertir en base64 avant de l'assigner au
 * champ Image (comportement 100% compatible avec un champ Image classique
 * si la webcam n'est pas disponible : l'upload manuel reste possible).
 */
export class WebcamImageField extends ImageField {
    static template = "adk_reception.WebcamImageField";

    setup() {
        super.setup();
        this.videoRef = useRef("adkWebcamVideo");
        this.canvasRef = useRef("adkWebcamCanvas");
        this.webcamState = useState({ streaming: false, error: null });
        this.stream = null;
    }

    async onOpenWebcam() {
        this.webcamState.error = null;
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            this.webcamState.streaming = true;
            // Le <video> n'est rendu qu'une fois streaming=true ; on attend le prochain tick.
            await new Promise((resolve) => setTimeout(resolve, 0));
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                await this.videoRef.el.play();
            }
        } catch (err) {
            this.webcamState.error = "Impossible d'accéder à la caméra (permissions ?).";
            this.webcamState.streaming = false;
        }
    }

    onCapture() {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas) {
            return;
        }
        canvas.width = video.videoWidth || 480;
        canvas.height = video.videoHeight || 360;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        const base64 = dataUrl.split(",")[1];
        this.props.record.update({ [this.props.name]: base64 });
        this.onCloseWebcam();
    }

    onCloseWebcam() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        this.webcamState.streaming = false;
    }
}

export const webcamImageField = {
    ...imageField,
    component: WebcamImageField,
};

registry.category("fields").add("adk_webcam", webcamImageField);
