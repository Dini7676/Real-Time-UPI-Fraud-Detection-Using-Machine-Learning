import os
import numpy as np
import joblib
import random
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "dataset")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "model")


def _safe_load(path):
    try:
        return np.load(path, allow_pickle=False)
    except ValueError:
        arr = np.load(path, allow_pickle=True)
        # Convert possible sparse/object arrays to dense numpy
        try:
            import scipy.sparse as sp  # type: ignore
            if sp.issparse(arr):
                return arr.toarray()
        except Exception:
            pass
        if isinstance(arr, np.ndarray) and arr.dtype == object:
            try:
                obj = arr.item() if arr.shape == () else arr[0]
                import scipy.sparse as sp  # type: ignore
                if sp.issparse(obj):
                    return obj.toarray()
                return np.array(obj)
            except Exception:
                return arr
        return arr


# Reproducibility
os.environ["PYTHONHASHSEED"] = "42"
np.random.seed(42)
random.seed(42)
tf.random.set_seed(42)

X_train = _safe_load(os.path.join(DATASET_DIR, "X_train.npy"))
X_test = _safe_load(os.path.join(DATASET_DIR, "X_test.npy"))
y_train = _safe_load(os.path.join(DATASET_DIR, "y_train.npy"))
y_test = _safe_load(os.path.join(DATASET_DIR, "y_test.npy"))

# Ensure dirs exist
os.makedirs(MODEL_DIR, exist_ok=True)

# Determine feature dimension
input_dim = X_train.shape[1]

# Traditional models
print("Training Logistic Regression (balanced)...")
log_reg = LogisticRegression(max_iter=300, class_weight='balanced', n_jobs=None)
log_reg.fit(X_train, y_train)
log_reg_pred = log_reg.predict(X_test)
print("LogReg Accuracy:", accuracy_score(y_test, log_reg_pred))
print("LogReg F1:", f1_score(y_test, log_reg_pred))

print("Training KNN...")
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train, y_train)
knn_pred = knn.predict(X_test)
print("KNN Accuracy:", accuracy_score(y_test, knn_pred))
print("KNN F1:", f1_score(y_test, knn_pred))

print("Training Random Forest (balanced)...")
rf = RandomForestClassifier(n_estimators=300, random_state=42, class_weight='balanced_subsample', max_depth=None)
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)
print("RF Accuracy:", accuracy_score(y_test, rf_pred))
print("RF F1:", f1_score(y_test, rf_pred))

# Save reports
with open(os.path.join(MODEL_DIR, "reports.txt"), "w") as f:
    f.write("LogReg\n")
    f.write(classification_report(y_test, log_reg_pred))
    f.write("\n\nKNN\n")
    f.write(classification_report(y_test, knn_pred))
    f.write("\n\nRandomForest\n")
    f.write(classification_report(y_test, rf_pred))

# CNN on tabular: use 1D Conv with sequence length = features
print("Training CNN (final model, class-weighted)...")
# Reshape to (samples, timesteps, channels)
X_train_cnn = np.expand_dims(X_train, axis=-1)
X_test_cnn = np.expand_dims(X_test, axis=-1)

model = keras.Sequential([
    layers.Input(shape=(input_dim, 1)),
    layers.Conv1D(32, kernel_size=3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.Conv1D(64, kernel_size=3, activation='relu', padding='same'),
    layers.BatchNormalization(),
    layers.GlobalAveragePooling1D(),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(1, activation='sigmoid'),
])

model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3),
              loss='binary_crossentropy',
              metrics=['accuracy'])

callbacks = [
    keras.callbacks.EarlyStopping(monitor='val_accuracy', patience=10, restore_best_weights=True),
]

# Compute class weights for Keras
from collections import Counter
counts = Counter(y_train.tolist())
total = sum(counts.values())
class_weight = {0: total/(2*counts.get(0,1)), 1: total/(2*counts.get(1,1))}

history = model.fit(
    X_train_cnn, y_train,
    validation_data=(X_test_cnn, y_test),
    epochs=60,
    batch_size=64,
    callbacks=callbacks,
    verbose=1,
    class_weight=class_weight,
)

cnn_eval = model.evaluate(X_test_cnn, y_test, verbose=0)
print(f"CNN Test Accuracy: {cnn_eval[1]:.4f}")

# Save final model
model.save(os.path.join(MODEL_DIR, "model1.h5"))
print("Saved CNN model to model/model1.h5")

# Also save RF model for optional offline analysis
joblib.dump(rf, os.path.join(MODEL_DIR, "rf_model.joblib"))
print("Saved RandomForest to model/rf_model.joblib")
