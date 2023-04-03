# -*- coding: utf-8 -*-
"""SQUAD.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vZg9SeEip_943ZEBdcgQop9URG1DNM4n

# 测试一下模型头 预测效果
"""

!pip install transformers datasets

import torch
from transformers import DistilBertForQuestionAnswering, DistilBertTokenizer


model = DistilBertForQuestionAnswering.from_pretrained("distilbert-base-uncased-distilled-squad")
tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

question = "What is the capital of France?"
context = "The capital of France is Paris."

inputs = tokenizer(question, context, return_tensors="pt")
input_ids = inputs["input_ids"].tolist()[0]


outputs = model(**inputs)
answer_start_scores = outputs.start_logits
answer_end_scores = outputs.end_logits

# 获取答案的开始和结束位置
answer_start = torch.argmax(answer_start_scores)
answer_end = torch.argmax(answer_end_scores)

# 将答案的token ID转换为文本
tokens = tokenizer.convert_ids_to_tokens(input_ids)
answer = tokens[answer_start : answer_end + 1]
answer = tokenizer.convert_tokens_to_string(answer)
print('Test Question:')
print("Question:", question)
print("Answer:", answer)

import torch
from datasets import load_dataset, load_metric
from transformers import DistilBertForQuestionAnswering, DistilBertTokenizerFast, TrainingArguments, Trainer

dataset = load_dataset("squad")

train_dataset = dataset["train"]
val_dataset = dataset["validation"]

train_dataset

model = DistilBertForQuestionAnswering.from_pretrained("distilbert-base-uncased")
tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")


max_length = 384
doc_stride = 128

def prepare_train_features(examples):

    tokenized_examples = tokenizer(
        examples["question"],
        examples["context"],
        max_length=max_length,
        truncation="only_second",
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        stride=doc_stride,
        padding="max_length",
    )

    sample_mapping = tokenized_examples.pop("overflow_to_sample_mapping")
    offset_mapping = tokenized_examples.pop("offset_mapping")

    tokenized_examples["start_positions"] = []
    tokenized_examples["end_positions"] = []

    for i, offsets in enumerate(offset_mapping):
        input_ids = tokenized_examples["input_ids"][i]
        cls_index = input_ids.index(tokenizer.cls_token_id)

        sequence_ids = tokenized_examples.sequence_ids(i)

        sample_index = sample_mapping[i]
        answers = examples["answers"][sample_index]

        if len(answers["answer_start"]) == 0:
            tokenized_examples["start_positions"].append(cls_index)
            tokenized_examples["end_positions"].append(cls_index)
        else:
            start_char = answers["answer_start"][0]
            end_char = start_char + len(answers["text"][0])

            token_start_index = 0
            while sequence_ids[token_start_index] != 1:
                token_start_index += 1

            token_end_index = len(input_ids) - 1
            while sequence_ids[token_end_index] != 1:
                token_end_index -= 1

            if not (offsets[token_start_index][0] <= start_char and offsets[token_end_index][1] >= end_char):
                tokenized_examples["start_positions"].append(cls_index)
                tokenized_examples["end_positions"].append(cls_index)
            else:
                while token_start_index < len(offsets) and offsets[token_start_index][0] <= start_char:
                    token_start_index += 1
                tokenized_examples["start_positions"].append(token_start_index - 1)

                while offsets[token_end_index][1] >= end_char:
                    token_end_index -= 1
                tokenized_examples["end_positions"].append(token_end_index + 1)

    return tokenized_examples


train_sample = train_dataset.select(range(200))
val_sample = val_dataset.select(range(200))

# 用sample测试一下
tokenized_train_sample = train_sample.map(prepare_train_features, batched=True, remove_columns=train_sample.column_names)
tokenized_val_sample = val_sample.map(prepare_train_features, batched=True, remove_columns=val_sample.column_names)

# tokenized_train_dataset = train_dataset.map(prepare_train_features, batched=True, remove_columns=train_dataset.column_names)
# tokenized_val_dataset = val_dataset.map(prepare_train_features, batched=True, remove_columns=val_dataset.column_names)
tokenized_train_sample = train_dataset.map(prepare_train_features, batched=True, remove_columns=train_dataset.column_names)
tokenized_val_sample = val_dataset.map(prepare_train_features, batched=True, remove_columns=val_dataset.column_names)

tokenized_train_sample

training_args = TrainingArguments(
    output_dir="./results",
    # 调整 - EPOCH
    num_train_epochs=3,   
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    evaluation_strategy="epoch",
    logging_dir="./logs",
    logging_strategy="steps",
    logging_steps=10,
    save_strategy="no",
    seed=42,
)


# 定义Trainer实例
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_sample,
    eval_dataset=tokenized_val_sample,
    tokenizer=tokenizer,
)

trainer.train()

preds = trainer.predict(tokenized_train_sample)

eval_results = trainer.evaluate()
print("Evaluation results:", eval_results)

# 获取答案文本和答案开始/结束位置

start_correct=[]
end_correct=[]
for i, (start_logits, end_logits) in enumerate(zip(preds.predictions[0], preds.predictions[1])):
    # 找到最大值的索引
    start_index = int(np.argmax(start_logits))
    end_index = int(np.argmax(end_logits))
    
    # 获取答案文本
    input_ids = tokenized_train_sample["input_ids"][i]
    answer_tokens = input_ids[start_index:end_index+1]
    answer_text = tokenizer.decode(answer_tokens)
    
    # 获取答案开始/结束位置
    start_pos = tokenized_train_sample["start_positions"][i]
    end_pos = tokenized_train_sample["end_positions"][i]

    if start_pos == start_index:
      start_correct.append(True)
    else:
      start_correct.append(False)

    if end_pos == end_index:
      end_correct.append(True)
    else:
      end_correct.append(False)

    # 打印结果
    print("Answer text:", answer_text)
    print("Answer start position (expected):", start_pos)
    print("Answer end position (expected):", end_pos)
    print("Answer start position (predicted):", start_index)
    print("Answer end position (predicted):", end_index)
    print("="*50)

print('start Accuracy:',start_correct.count(True)/len(start_correct))
print('End Accuracy:',end_correct.count(True)/len(end_correct))
print('AVG Accuracy:',1/2*(start_correct.count(True)/len(start_correct) + end_correct.count(True)/len(end_correct)))

"""# 保存模型"""

model_save_path = "./distilbert_squad"
trainer.save_model(model_save_path)
tokenizer.save_pretrained(model_save_path)





