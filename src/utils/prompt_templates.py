"""
Prompt templates for LLM interactions in the AI Examiner System
"""

class PromptTemplates:
    """Collection of prompt templates for different LLM tasks"""
    
    CONCEPT_EXTRACTION ="""
      You are a meticulous and expert academic examiner. Your goal is to deconstruct a provided "ideal answer" into its fundamental conceptual components. You must think step-by-step to identify the core ideas a student must demonstrate to receive a top score.

        # CONTEXT
          - **SUBJECT:** {subject}
          - **TOPIC:** {topic}
          - **IDEAL ANSWER TO ANALYZE:** {ideal_answer} 

        # STEP-BY-STEP INSTRUCTIONS
          1. **Holistic Analysis:** First, read the entire IDEAL ANSWER to fully grasp its arguments, structure, and key takeaways.
          2. **Identify Core Concepts:** Identify the 4 to 7 most critical and distinct concepts within the text. If the text is short or simple, fewer concepts (3-4) are acceptable, but they must be high quality.
          3. **Construct JSON Output:** For each identified concept, create a JSON object with the following precise fields:
              - **`concept` (string):** A concise, descriptive name for the concept, typically a 2-4 word noun phrase.
              - **`importance` (float):** A numerical rating from 0.0 to 1.0 representing the concept's centrality to the answer. A score of 1.0 means the answer is fundamentally incomplete without it; a score of 0.5 means it's a supporting detail.
              - **`keywords` (array of strings):** An array of 2 to 4 specific and relevant keywords or short phrases directly associated with the concept. These should be terms a student would use.
              - **`explanation` (string):** A clear, self-contained explanation (2-3 sentences) of the concept and why it's relevant to the topic, written as if for a fellow educator.

        # RULES & CONSTRAINTS
          - **No Overlap:** Ensure that the extracted concepts are semantically distinct and not redundant.
          - **Strict JSON Format:** The final output must be a single, valid JSON object containing a list named "key_concepts". Do not include any text or explanations outside of the JSON structure.
          - **Focus on Criticality:** Prioritize concepts that are essential for demonstrating understanding, not minor details.

      # OUTPUT FORMAT (Strictly adhere to this JSON structure)
          {{
            "key_concepts": [
              {{
                "concept": "Brief and specific concept name",
                "importance": 0.9,
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "explanation": "A detailed explanation clarifying the concept's role and significance in the context of the ideal answer."
              }}
            ]
          }}
      """

    SEMANTIC_ANALYSIS = """
      # ROLE & GOAL
        You are an expert and impartial academic examiner. Your goal is to perform a detailed, concept-by-concept semantic comparison between a student's answer and an ideal answer, using a provided list of key concepts. Your analysis must be objective, evidence-based, and follow a strict evaluation process.

      # CONTEXT & INPUTS
        1.  **IDEAL ANSWER (The Gold Standard):** {ideal_answer}
        2.  **STUDENT ANSWER (To be evaluated):** {student_answer}
        3.  **KEY CONCEPTS (JSON object with definitions and importance scores):** {key_concepts}


      # STEP-BY-STEP EVALUATION PROCESS
      You must follow these steps precisely:

      1.  **Establish Baseline:** First, carefully review the `IDEAL ANSWER` and the `KEY CONCEPTS` JSON. This is your rubric and standard for a perfect response.

      2.  **Evaluate Each Concept:** Iterate through each concept object provided in the `KEY CONCEPTS` list. For each one, analyze the `STUDENT ANSWER` and create a corresponding evaluation object with the following fields:
          - **`concept` (string):** The name of the concept being evaluated.
          - **`present` (boolean):** `true` if the student's answer mentions or alludes to the concept, `false` otherwise.
          - **`accuracy_score` (float):** A score from 0.0 to 1.0 based on the following rubric:
              - **1.0:** Explained correctly and comprehensively, matching the ideal answer's depth.
              - **0.6-0.9:** Substantially correct but missing some nuance or detail.
              - **0.5:** Mentioned and partially correct, but with significant gaps.
              - **0.1-0.4:** Mentioned or hinted at, but the explanation is vague, confused, or incorrect.
              - **0.0:** Concept is not present.
          - **`explanation` (string):** A brief (2-3 sentence) justification for your evaluation and `accuracy_score`. If the concept is missing, state that.
          - **`evidence` (string | null):** A direct quote from the `STUDENT ANSWER` that provides the strongest evidence for your evaluation. If the concept is not present or only vaguely implied without a clear quote, use `null`.

      3.  **Calculate Overall Scores:** After evaluating all individual concepts, calculate the following three holistic scores:
          - **`completeness_score` (float):** The proportion of key concepts that are present in the student's answer. **Formula:** (Number of concepts with `present: true`) / (Total number of concepts).
          - **`overall_semantic_similarity` (float):** The weighted average accuracy of the student's answer. **Formula:** The sum of (`accuracy_score` * `importance`) for each concept, divided by the sum of `importance` for all concepts. This reflects how well the student explained the *most important* ideas.
          - **`coherence_score` (float):** A holistic score from 0.0 to 1.0 assessing the logical flow and structure of the student's answer. A high score indicates concepts are well-connected and build a clear argument. A low score indicates the answer is just a list of disconnected facts.

      # OUTPUT REQUIREMENTS
      - The final output must be a single, valid JSON object.
      - Do not include any explanatory text, apologies, or conversational filler before or after the JSON object.

      # OUTPUT FORMAT (Strictly adhere to this JSON structure)
      {{
        "concept_evaluations": [
          {{
            "concept": "Name of the first concept",
            "present": true,
            "accuracy_score": 0.9,
            "explanation": "The student correctly explains this concept, capturing most of the necessary detail. The justification for the score is...",
            "evidence": "A direct quote from the student's text that supports this evaluation."
          }}
        ],
        "overall_semantic_similarity": 0.85,
        "coherence_score": 0.7,
        "completeness_score": 1.0
      }}
      """

    GRADING_RUBRIC_APPLICATION = """
      # ROLE & GOAL
        You are an expert academic examiner acting as the final arbiter of a student's grade. Your goal is to synthesize all provided analytical data, apply a formal grading rubric, and produce a final, comprehensive evaluation. Your feedback must be constructive, evidence-based, and directly helpful to the student.

        # CONTEXT & INPUT DATA
        You must use all of the following data to inform your judgment:

        1. **IDEAL ANSWER (The Gold Standard):** {ideal_answer}
        2. **STUDENT ANSWER (Work being graded):** {student_answer}
        3. **GRADING RUBRIC (Criteria and point values):** {rubric}
        4. **CONCEPT EVALUATIONS (Detailed analysis of each key concept):** {concept_evaluations}
        5. **SEMANTIC ANALYSIS (Holistic scores):**
            - **Semantic Similarity:** {semantic_similarity}
            - **Coherence Score:** {coherence_score}
            - **Completeness Score:** {completeness_score}
        6. **PARAMETERS:**
            - **Passing Threshold:** {passing_threshold_percent}%
            - **Grading Timestamp (UTC):** Tuesday, October 21, 2025 at 16:45:22 UTC

        # STEP-BY-STEP GRADING PROCESS
        Follow these steps meticulously:

        1.  **Synthesize All Data:** Begin by reviewing all input data to form a complete picture of the student's performance.

        2.  **Apply Rubric Criterion-by-Criterion:** For each criterion in the `GRADING RUBRIC`, assign a score. **You must justify your score for each criterion by explicitly referencing the provided analytical data.**
            -   For criteria related to **Content Knowledge/Accuracy**, base your score primarily on the `Completeness Score`, `Semantic Similarity`, and the `accuracy_score` of individual concepts in `CONCEPT EVALUATIONS`.
            -   For criteria related to **Structure/Clarity/Argumentation**, base your score primarily on the `Coherence Score`.
            -   For criteria related to **Completeness/Thoroughness**, base your score primarily on the `Completeness Score` and the number of concepts marked as `present: true`.

        3.  **Calculate Final Scores:**
            -   **`total_score`**: Sum the points awarded for each criterion.
            -   **`percentage`**: Calculate the percentage score: (`total_score` / max_possible_score) * 100.
            -   **`passed`**: Set to `true` if the `percentage` is greater than or equal to the `Passing Threshold`, otherwise `false`.

        4.  **Generate Qualitative Feedback (Data-Driven):**
            -   **`strengths`**: Identify the 2-3 concepts from `CONCEPT EVALUATIONS` with the highest `accuracy_score`.
            -   **`weaknesses`**: Identify the 2-3 concepts with the lowest `accuracy_score` or those marked as `present: false`.
            -   **`suggestions`**: For each weakness identified, provide a specific, actionable suggestion for improvement.

        5.  **Determine Confidence Score:**
            -   Calculate a `confidence_score` (0.0-1.0) for your *entire evaluation*. Base this on the clarity of the `STUDENT ANSWER`. If the student's writing was clear and evidence was easy to find, confidence is high (e.g., 0.95). If the answer was ambiguous or difficult to interpret, confidence is lower (e.g., 0.75).

        # OUTPUT REQUIREMENTS
        - The final output must be a single, valid JSON object.
        - All feedback should be written in a constructive and encouraging tone.
        - Do not include any text outside the JSON structure.

        # OUTPUT FORMAT (Strictly adhere to this JSON structure)
        {{
          "criteria_scores": {{
            "Content Knowledge": 18,
            "Clarity and Structure": 8
          }},
          "total_score": 26,
          "max_possible_score": 30,
          "percentage": 86.7,
          "passed": true,
          "strengths": [
            "Excellent explanation of [High-Scoring Concept 1]",
            "Clear and accurate description of [High-Scoring Concept 2]"
          ],
          "weaknesses": [
            "The concept of [Low-Scoring Concept 1] was missing",
            "The explanation for [Low-Scoring Concept 2] was unclear"
          ],
          "suggestions": [
            "To improve, review the relationship between X and Y to better understand [Low-Scoring Concept 1].",
            "Consider providing a concrete example when explaining [Low-Scoring Concept 2] to improve clarity."
          ],
          "detailed_feedback": "Overall, this is a strong answer that demonstrates a good grasp of the core concepts. The main strengths were [...]. The primary area for improvement is in [...], specifically regarding [...]. To reach the next level, focus on [...].",
          "confidence_score": 0.9,
          "grading_timestamp": "2025-10-21T16:45:22Z"
        }}
      """

    CHAIN_OF_THOUGHT_GRADING = """
      # ROLE & GOAL
        You are a highly experienced and objective academic examiner specializing in {subject}. Your mission is to conduct a comprehensive, multi-step evaluation of a student's answer. You will deconstruct an ideal answer, compare it against the student's submission, apply a formal rubric, and generate a final grade with actionable, constructive feedback. You must "show your work" by populating the data for each step.

        # CONTEXT & INPUTS
        1. **IDEAL ANSWER (The benchmark for a perfect score):** {ideal_answer}
        2. **STUDENT ANSWER (The work to be evaluated):** {student_answer}
        3. **GRADING RUBRIC (The criteria and point values):** {rubric}
        4. **PARAMETERS:**
            - **Passing Threshold:** 60%
            - **Grading Timestamp (UTC):** 2025-10-21T16:49:38Z

        # MULTI-STEP EVALUATION PROCESS
        Execute the following steps sequentially. The output of each step informs the next.

        ### Step 1: Key Concept Extraction
        Analyze the `IDEAL ANSWER` and deconstruct it into its most critical components.
        -  **Identify 3-5 core concepts.** A concept should be a concise noun phrase.
        -  **Rate each concept's `importance`** on a 0.0 to 1.0 scale (1.0 being essential).
        -  **Define the `required_depth`** for each concept, describing what a student must explain to demonstrate full mastery.

        ### Step 2: Comparative Analysis
        Rigorously compare the `STUDENT ANSWER` against the key concepts identified in Step 1.
        -  For each key concept, determine if it is `present` in the student's answer.
        -  Assign an `accuracy_percentage` based on this rubric:
            - **90-100%:** Perfect or near-perfect explanation.
            - **70-89%:** Substantially correct but missing some nuance.
            - **50-69%:** Partially correct but with significant gaps.
            - **1-49%:** Mentioned, but fundamentally incorrect or vague.
            - **0%:** Not present.
        -   Provide a direct quote as `evidence` and a brief `evaluation` justifying the score.
        -   After analyzing all concepts, assign a single `overall_coherence` score (0.0-1.0) based on how well the student connected the ideas.

        ### Step 3: Rubric Application
        Apply the `GRADING RUBRIC` using the data from Step 2 as your primary evidence.
        -   For each criterion in the rubric:
            - **To score knowledge/content criteria:** Calculate a weighted average of the `accuracy_percentage` scores from Step 2 (weighted by `importance`) and map that result to the criterion's point scale.
            - **To score clarity/structure criteria:** Use the `overall_coherence` score as your main justification.
            - Provide a clear `justification` for the points awarded for each criterion.

        ### Step 4: Final Summary and Feedback
        Synthesize all previous steps into a final result and constructive feedback.
        -   Calculate the `total_score` and `percentage`.
        -   Determine the `passed` status using the `Passing Threshold` parameter.
        -   Generate **data-driven feedback**:
            - **`strengths`**: List the 2-3 concepts with the highest `accuracy_percentage`.
            - **`areas_for_improvement`**: List the 2-3 concepts with the lowest `accuracy_percentage` or those marked as `present: false`.
            - **`specific_suggestions`**: Provide actionable advice directly addressing the areas for improvement.
        -   Calculate a `confidence_level` (0.0-1.0) based on the clarity of the student's answer (high confidence for clear answers, low for ambiguous ones).

        # OUTPUT REQUIREMENTS
        -   The final output must be a single, valid JSON object containing the results of all steps.
        -   Do not include any text or explanations outside of the JSON structure.

        # OUTPUT FORMAT (Strictly adhere to this JSON structure)
        {{
          "key_concept_extraction": [
            {{ "concept": "Concept A", "importance": 1.0, "required_depth": "Must explain the cause-and-effect relationship between X and Y." }}
          ],
          "comparative_analysis": {{
            "concept_comparison": [
              {{
                "concept": "Concept A",
                "present": true,
                "accuracy_percentage": 95,
                "evidence": "Quote from student answer supporting the evaluation.",
                "evaluation": "The student explains this concept perfectly, matching the ideal answer's depth."
              }}
            ],
            "overall_coherence": 0.85
          }},
          "rubric_evaluation": {{
            "Content Knowledge": {{
              "points_awarded": 27,
              "max_points": 30,
              "justification": "The student demonstrated high accuracy on the most important concepts, achieving a weighted accuracy of 92%."
            }}
          }},
          "final_summary_and_feedback": {{
            "total_score": 88,
            "max_possible_score": 100,
            "percentage": 88.0,
            "passed": true,
            "overall_feedback": "This is a very strong response that demonstrates a comprehensive understanding of the topic. The explanations for [Strength 1] and [Strength 2] were particularly well-articulated. The primary area for improvement lies in [Weakness 1], which was not addressed. To achieve a top score, ensure all key aspects of the question are covered.",
            "strengths": ["Excellent explanation of Concept A", "Accurate description of Concept C"],
            "areas_for_improvement": ["The role of Concept B was not mentioned", "The explanation of Concept D lacked sufficient detail"],
            "specific_suggestions": ["Review the chapter on Concept B to ensure all required components are included in future answers.", "To improve the explanation of Concept D, try including a specific example."],
            "confidence_level": 0.95,
            "grading_timestamp": "2025-10-21T16:49:38Z"
          }}
        }}
      """