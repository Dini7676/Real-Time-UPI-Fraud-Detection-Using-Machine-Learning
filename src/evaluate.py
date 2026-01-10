import os
import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report

ROOT = os.path.dirname(__file__)
DATASET_DIR = os.path.join(ROOT, '..', 'dataset')
MODEL_DIR = os.path.join(ROOT, '..', 'model')

X_test_path = os.path.join(DATASET_DIR, 'X_test.npy')
y_test_path = os.path.join(DATASET_DIR, 'y_test.npy')
model_path = os.path.join(MODEL_DIR, 'model1.h5')
report_path = os.path.join(MODEL_DIR, 'eval_report.txt')

if not os.path.exists(X_test_path) or not os.path.exists(y_test_path):
    raise SystemExit('Missing X_test.npy or y_test.npy. Run preprocess.py first.')
if not os.path.exists(model_path):
    raise SystemExit('Missing model/model1.h5. Run train.py first.')

X_test = np.load(X_test_path, allow_pickle=False)
y_test = np.load(y_test_path, allow_pickle=False)

# Reshape for CNN model: (samples, features, 1)
X_test_cnn = np.expand_dims(X_test, axis=-1)

model = tf.keras.models.load_model(model_path)
proba = model.predict(X_test_cnn, verbose=0).reshape(-1)

# Threshold from env (default 0.5 for evaluation clarity)
threshold = float(os.getenv('FRAUD_THRESHOLD', '0.5'))
y_pred = (proba >= threshold).astype(int)

acc = accuracy_score(y_test, y_pred)
prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary', zero_division=0)
cm = confusion_matrix(y_test, y_pred)
crep = classification_report(y_test, y_pred)

os.makedirs(MODEL_DIR, exist_ok=True)
with open(report_path, 'w') as f:
    f.write(f"Threshold: {threshold}\n")
    f.write(f"Accuracy: {acc:.4f}\n")
    f.write(f"Precision: {prec:.4f}  Recall: {rec:.4f}  F1: {f1:.4f}\n\n")
    f.write("Confusion Matrix (rows=true [0,1], cols=pred [0,1]):\n")
    f.write(str(cm))
    f.write("\n\nClassification Report:\n")
    f.write(crep)

print('Evaluation complete. See model/eval_report.txt')
