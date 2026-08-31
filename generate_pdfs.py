"""Generate two PDFs: one with questions only, one with full answer context."""

from fpdf import FPDF

QUESTIONS = [
    {"id":"NN-001","type":"MCQ","difficulty":"easy","question":"What is a Neural Network inspired by?","options":["Computer processors","The human brain and biological neurons","Statistical equations","Database systems"],"answer":"The human brain and biological neurons","explanation":"Artificial Neural Networks (ANN) are inspired by how biological neurons in the human brain communicate. Just as neurons pass signals through synapses, artificial neurons pass weighted signals through layers."},
    {"id":"NN-002","type":"MCQ","difficulty":"easy","question":"Which of the following is NOT a layer type in a basic Neural Network?","options":["Input Layer","Hidden Layer","Output Layer","Processing Layer"],"answer":"Processing Layer","explanation":"A basic Neural Network has three layer types: Input Layer (receives features), Hidden Layer(s) (processes and transforms data), and Output Layer (produces final prediction). There is no 'Processing Layer' — that is not standard terminology."},
    {"id":"NN-003","type":"MCQ","difficulty":"easy","question":"What is the role of an Activation Function in a Neural Network?","options":["To initialize weights","To introduce non-linearity so the network can learn complex patterns","To calculate the cost function","To split data into training and testing sets"],"answer":"To introduce non-linearity so the network can learn complex patterns","explanation":"Without activation functions, a neural network would just be a linear equation no matter how many layers. Activation functions like ReLU, Sigmoid, and Tanh add non-linearity, allowing the network to learn complex, non-linear patterns."},
    {"id":"NN-004","type":"MCQ","difficulty":"medium","question":"What is the ReLU activation function formula?","options":["f(x) = 1/(1+e^-x)","f(x) = max(0, x)","f(x) = (e^x - e^-x)/(e^x + e^-x)","f(x) = x^2"],"answer":"f(x) = max(0, x)","explanation":"ReLU (Rectified Linear Unit) = max(0, x). It outputs x if x > 0, and 0 if x <= 0. ReLU is computationally efficient and avoids the vanishing gradient problem."},
    {"id":"NN-005","type":"MCQ","difficulty":"medium","question":"What is Backpropagation in Neural Networks?","options":["Forward pass of data through all layers","Algorithm to update weights by propagating error backwards from output to input","Process of initializing weights randomly","Method to add more hidden layers"],"answer":"Algorithm to update weights by propagating error backwards from output to input","explanation":"Backpropagation calculates the gradient of the loss function with respect to each weight using the chain rule. These gradients are used by Gradient Descent to update weights — this is how the neural network learns."},
    {"id":"NN-006","type":"MCQ","difficulty":"medium","question":"What is a Convolutional Neural Network (CNN) primarily used for?","options":["Text generation","Image and spatial data processing","Time series prediction only","Clustering unlabelled data"],"answer":"Image and spatial data processing","explanation":"CNNs use convolutional layers to automatically detect features in images — edges, shapes, textures. They are the standard choice for medical image analysis, X-ray classification, and tumour detection."},
    {"id":"NN-007","type":"MCQ","difficulty":"medium","question":"What problem does the Dropout regularization technique solve?","options":["Underfitting","Overfitting","Slow convergence","Missing data"],"answer":"Overfitting","explanation":"Dropout randomly deactivates a fraction of neurons during each training iteration, preventing the network from over-relying on specific neurons and forcing it to learn more robust features."},
    {"id":"NN-008","type":"MCQ","difficulty":"hard","question":"What is the Vanishing Gradient problem?","options":["When gradients become too large during backpropagation","When gradients become extremely small during backpropagation, making early layers learn very slowly","When the model fails to converge at all","When weights are initialized to zero"],"answer":"When gradients become extremely small during backpropagation, making early layers learn very slowly","explanation":"In deep networks with sigmoid/tanh activations, gradients shrink during backpropagation and become tiny near input layers. ReLU and batch normalization help solve this."},
    {"id":"NN-009","type":"MCQ","difficulty":"hard","question":"In CNN architecture, what does a Pooling Layer do?","options":["Adds more features to the feature map","Reduces the spatial dimensions of the feature map while retaining important features","Applies activation functions to neurons","Connects all neurons in one layer to all neurons in the next"],"answer":"Reduces the spatial dimensions of the feature map while retaining important features","explanation":"Pooling (Max or Average) reduces width and height of feature maps, lowering computational cost and controlling overfitting. Max Pooling takes the maximum value in each window, preserving prominent features."},
    {"id":"NN-010","type":"MCQ","difficulty":"hard","question":"What is the difference between a shallow neural network and a deep neural network?","options":["Shallow has 1 hidden layer; Deep has 2 or more hidden layers","Shallow uses ReLU; Deep uses Sigmoid","Shallow is for regression; Deep is for classification","Shallow trains faster always; Deep trains slower always"],"answer":"Shallow has 1 hidden layer; Deep has 2 or more hidden layers","explanation":"Deep Learning refers to neural networks with multiple hidden layers. More layers allow learning increasingly abstract representations — from edges to shapes to objects in image recognition tasks."},
    {"id":"NN-011","type":"TrueFalse","difficulty":"easy","question":"A Neural Network with zero hidden layers is equivalent to Logistic Regression.","answer":"True","explanation":"A neural network with no hidden layers and a sigmoid output is mathematically equivalent to Logistic Regression. Hidden layers are what give neural networks their extra power."},
    {"id":"NN-012","type":"TrueFalse","difficulty":"medium","question":"Increasing the number of layers always improves a Neural Network's performance.","answer":"False","explanation":"More layers can lead to overfitting, vanishing gradients, and slower training without better accuracy. The right depth depends on the problem and data size."},
    {"id":"NN-013","type":"TrueFalse","difficulty":"medium","question":"CNNs are the standard architecture for medical image classification tasks.","answer":"True","explanation":"CNNs automatically learn spatial features through convolution. They are used in chest X-ray classification, tumour detection, retinal disease diagnosis, and skin lesion classification."},
    {"id":"NN-014","type":"TrueFalse","difficulty":"hard","question":"Batch Normalization speeds up training by normalizing inputs to each layer.","answer":"True","explanation":"Batch Normalization normalizes layer inputs to mean=0 and variance=1 within each mini-batch, reducing internal covariate shift and allowing higher learning rates."},
    {"id":"NN-015","type":"ShortAnswer","difficulty":"easy","question":"Explain how a Neural Network learns with a simple analogy.","answer":"A Neural Network learns like a student studying for an exam. Step 1 - Forward Pass: student gives an answer (prediction). Step 2 - Calculate Error: teacher marks it right or wrong (loss function). Step 3 - Backpropagation: student understands which concepts were wrong (gradient flows back). Step 4 - Weight Update: student studies harder on weak areas (Gradient Descent updates weights). Step 5 - Repeat for many examples (epochs) until performance improves.","explanation":"This forward-backward learning cycle is called an epoch. Multiple epochs on training data gradually reduce the error."},
    {"id":"NN-016","type":"ShortAnswer","difficulty":"medium","question":"What are the main components of a CNN architecture? Explain each briefly.","answer":"1) Input Layer - receives raw image as pixel matrix. 2) Convolutional Layer - applies filters to detect features (edges, textures). 3) Activation (ReLU) - adds non-linearity. 4) Pooling Layer - reduces spatial dimensions. 5) Flatten - converts 2D maps to 1D vector. 6) Fully Connected Layer - combines all features. 7) Output Layer - final classification (Softmax or Sigmoid).","explanation":"Understanding CNN architecture is essential for medical imaging tasks like X-ray diagnosis and tumour detection."},
    {"id":"NN-017","type":"ShortAnswer","difficulty":"hard","question":"Explain Transfer Learning and why it is especially useful in biomedical AI.","answer":"Transfer Learning uses a pre-trained network (trained on millions of images) and fine-tunes it on a smaller domain-specific dataset. Useful in biomedical AI because: 1) Medical labelled data is scarce and expensive to annotate. 2) Pre-trained features (edges, textures) transfer well to medical images. 3) Fine-tuning is much faster than training from scratch. Example: ResNet or VGG16 trained on ImageNet fine-tuned for chest X-ray classification.","explanation":"Transfer learning is why modern medical AI systems can achieve high accuracy with relatively small datasets."},
    {"id":"NN-018","type":"MCQ","difficulty":"easy","question":"What activation function is used in the output layer for binary classification?","options":["ReLU","Sigmoid","Softmax","Tanh"],"answer":"Sigmoid","explanation":"Sigmoid outputs a value between 0 and 1, interpreted as a probability for binary classification. For multi-class classification, Softmax is used instead."},
    {"id":"NN-019","type":"MCQ","difficulty":"medium","question":"What is an Epoch in Neural Network training?","options":["One single weight update","One complete pass through the entire training dataset","One layer of the neural network","One batch of training samples"],"answer":"One complete pass through the entire training dataset","explanation":"An epoch is one complete pass through all training samples. Training typically requires many epochs (50-500+) until the model converges. Too many epochs leads to overfitting."},
    {"id":"NN-020","type":"ShortAnswer","difficulty":"hard","question":"How does a CNN detect diseases in medical images? Explain with reference to chest X-ray analysis.","answer":"1) Input - Chest X-ray image as pixel matrix (e.g. 224x224). 2) First Conv Layers - detect low-level features: edges, bone outlines. 3) Middle Layers - detect medium-level features: rib shapes, lung boundaries. 4) Deep Layers - detect high-level features: consolidation (pneumonia), nodules (tumour), effusion signs. 5) Fully Connected - combines all features. 6) Output - probability scores per class (e.g. Normal=0.12, Pneumonia=0.78). 7) Prediction - highest probability class selected.","explanation":"Each CNN layer learns increasingly complex features automatically — no manual feature engineering needed."},
]

OPTION_LETTERS = ["A", "B", "C", "D"]
DIFFICULTY_TAG = {"easy": "[Easy]", "medium": "[Medium]", "hard": "[Hard]"}
TYPE_LABEL = {"MCQ": "Multiple Choice", "TrueFalse": "True / False", "ShortAnswer": "Short Answer"}


def clean(text: str) -> str:
    """Replace non-latin-1 characters so fpdf core fonts don't reject them."""
    return (
        text.replace("\u2014", "-")   # em dash
            .replace("\u2013", "-")   # en dash
            .replace("\u2018", "'")   # left single quote
            .replace("\u2019", "'")   # right single quote
            .replace("\u201c", '"')   # left double quote
            .replace("\u201d", '"')   # right double quote
            .replace("\u2264", "<=")  # less-than-or-equal
            .replace("\u2265", ">=")  # greater-than-or-equal
    )


class BasePDF(FPDF):
    def __init__(self, title):
        super().__init__()
        self._title = title

    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 10, self._title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, "Topic: Neural Networks", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


# ── PDF 1: Questions only ─────────────────────────────────────────────────────
def build_questions_pdf():
    pdf = BasePDF("Neural Networks - Practice Questions")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    for i, q in enumerate(QUESTIONS, 1):
        tag = TYPE_LABEL.get(q["type"], q["type"])
        diff = DIFFICULTY_TAG.get(q["difficulty"], "")

        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 7, clean(f"Q{i}.  ({tag})  {diff}"), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, clean(q["question"]), new_x="LMARGIN", new_y="NEXT")

        if q["type"] == "MCQ":
            for letter, opt in zip(OPTION_LETTERS, q.get("options", [])):
                pdf.set_x(28)
                pdf.multi_cell(0, 6, clean(f"{letter}.  {opt}"), new_x="LMARGIN", new_y="NEXT")

        elif q["type"] == "TrueFalse":
            pdf.set_x(28)
            pdf.cell(0, 6, "A.  True                    B.  False", new_x="LMARGIN", new_y="NEXT")

        elif q["type"] == "ShortAnswer":
            for _ in range(5):
                pdf.ln(1)
                pdf.set_draw_color(150, 150, 150)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.ln(7)

        pdf.ln(5)

    pdf.output("neural_networks_questions.pdf")
    print("Saved: neural_networks_questions.pdf")


# ── PDF 2: Context / Answer Reference ────────────────────────────────────────
def build_context_pdf():
    pdf = BasePDF("Neural Networks - Answer Context & Reference")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Intro paragraph
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "About This Reference", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(235, 245, 255)
    pdf.multi_cell(
        0, 6,
        "This document contains the complete answer context for all 20 Neural Networks "
        "practice questions. Each entry includes the correct answer and a detailed "
        "explanation grounded in core Deep Learning theory. Use this as a study reference "
        "after attempting the question paper independently.",
        new_x="LMARGIN", new_y="NEXT", fill=True,
    )
    pdf.ln(6)

    for i, q in enumerate(QUESTIONS, 1):
        tag = TYPE_LABEL.get(q["type"], q["type"])
        diff = DIFFICULTY_TAG.get(q["difficulty"], "")

        # Question label
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.multi_cell(0, 7, clean(f"Q{i}.  ({tag})  {diff}  -  {q['question']}"), new_x="LMARGIN", new_y="NEXT", fill=True)

        # Correct answer
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 120, 0)
        pdf.multi_cell(0, 6, clean(f"Answer:  {q['answer']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        # Explanation
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 5, clean(q["explanation"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

    pdf.output("neural_networks_context.pdf")
    print("Saved: neural_networks_context.pdf")


if __name__ == "__main__":
    build_questions_pdf()
    build_context_pdf()
