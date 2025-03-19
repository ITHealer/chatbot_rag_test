from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate



QuestionAnswerTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(
                template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
                        You are an AI assistant designed for accurate information retrieval and question answering.
                        - Think careful before answer.
                        - Answer this "{input}" question should be based on "{context}". If you don't know the answer, just say "I couldn't find an answer because the question involves information that has not been documented or is unavailable in the training data." 
                        <|eot_id|>
                         """,
                input_variables=['context', 'input']
            )
        ),
        HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                template="""
                        <|start_header_id|>user<|end_header_id|>
                            - Answer the {input} question strictly based on the given {context}.
                            - Do not rely on external knowledge or make assumptions.
                        <|eot_id|><|start_header_id|>assistant<|end_header_id|>
                         """,
                input_variables=['context', 'input']
            )
        )
    ]
)


ContextualizeQuestionHistoryTemplate = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(
            prompt=PromptTemplate(
                template="""
                    You are a context-aware AI Assistant, dedicated to following instructions precisely without providing any opinions. 
                    Your task is to reformulate the latest user question.
                    Do not rewrite short form of word
                    Ensure the reformulated question is clear, coherent, no yapping and self-contained, providing all necessary context.
                    Your mission is to Formulate the latest User Question into a standalone question that can be understood without the chat history, if necessary, or return it unchanged.
                    IMPORTANT: DO NOT answer the Latest User Question.
                    """,
                input_variables=[]
            )
        ),
        HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                template="""
                <The Latest User Question>: {input} 

                Note: 
                - Your mission is to formulate a standalone question.
                - DO NOT answer the question, just reformulate it if needed and otherwise return it as is.
                - No explaination, just return result.
                    
                Standalone question: """,
                input_variables=['input'],
            )
        )
    ]
)

