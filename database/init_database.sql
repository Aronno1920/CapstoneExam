-- =============================================
-- AI Examiner System Database Setup Script
-- Database: MSSQL Server
-- Version: 1.0
-- Created: 2024
-- =============================================

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'AIExaminerDB')
BEGIN
    CREATE DATABASE AIExaminerDB;
    PRINT 'Database AIExaminerDB created successfully.';
END
ELSE
BEGIN
    PRINT 'Database AIExaminerDB already exists.';
END
GO

-- Use the database
USE AIExaminerDB;
GO

-- =============================================
-- DROP EXISTING TABLES (if they exist)
-- =============================================
IF OBJECT_ID('concept_evaluations', 'U') IS NOT NULL DROP TABLE concept_evaluations;
IF OBJECT_ID('grading_results', 'U') IS NOT NULL DROP TABLE grading_results;
IF OBJECT_ID('student_answers', 'U') IS NOT NULL DROP TABLE student_answers;
IF OBJECT_ID('rubric_criteria', 'U') IS NOT NULL DROP TABLE rubric_criteria;
IF OBJECT_ID('key_concepts', 'U') IS NOT NULL DROP TABLE key_concepts;
IF OBJECT_ID('questions', 'U') IS NOT NULL DROP TABLE questions;
IF OBJECT_ID('grading_sessions', 'U') IS NOT NULL DROP TABLE grading_sessions;
IF OBJECT_ID('audit_logs', 'U') IS NOT NULL DROP TABLE audit_logs;
GO

-- =============================================
-- CREATE TABLES
-- =============================================

-- Questions table - stores questions and their ideal answers
CREATE TABLE questions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    question_id NVARCHAR(255) NOT NULL UNIQUE,
    subject NVARCHAR(100) NOT NULL,
    topic NVARCHAR(255) NOT NULL,
    question_text NTEXT NOT NULL,
    ideal_answer NTEXT NOT NULL,
    max_marks FLOAT NOT NULL CHECK (max_marks > 0),
    passing_threshold FLOAT DEFAULT 60.0 CHECK (passing_threshold >= 0 AND passing_threshold <= 100),
    difficulty_level NVARCHAR(50) DEFAULT 'intermediate' CHECK (difficulty_level IN ('easy', 'intermediate', 'hard', 'expert')),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Key concepts extracted from ideal answers
CREATE TABLE key_concepts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    question_id INT NOT NULL,
    concept_name NVARCHAR(255) NOT NULL,
    concept_description NTEXT NOT NULL,
    importance_score FLOAT NOT NULL CHECK (importance_score >= 0 AND importance_score <= 1),
    keywords NTEXT, -- JSON array of keywords
    max_points FLOAT NOT NULL CHECK (max_points >= 0),
    extraction_method NVARCHAR(50) DEFAULT 'llm_extracted' CHECK (extraction_method IN ('llm_extracted', 'manual')),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Grading rubric criteria for questions
CREATE TABLE rubric_criteria (
    id INT IDENTITY(1,1) PRIMARY KEY,
    question_id INT NOT NULL,
    criteria_name NVARCHAR(255) NOT NULL,
    criteria_description NTEXT NOT NULL,
    max_points FLOAT NOT NULL CHECK (max_points >= 0),
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0 AND weight <= 1),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Student submitted answers
CREATE TABLE student_answers (
    id INT IDENTITY(1,1) PRIMARY KEY,
    answer_id NVARCHAR(255) NOT NULL UNIQUE DEFAULT NEWID(),
    student_id NVARCHAR(255) NOT NULL,
    question_id INT NOT NULL,
    answer_text NTEXT NOT NULL,
    submitted_at DATETIME2 DEFAULT GETUTCDATE(),
    language NVARCHAR(10) DEFAULT 'en',
    word_count INT,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- AI grading results
CREATE TABLE grading_results (
    id INT IDENTITY(1,1) PRIMARY KEY,
    result_id NVARCHAR(255) NOT NULL UNIQUE DEFAULT NEWID(),
    student_answer_id INT NOT NULL,
    
    -- Scores
    total_score FLOAT NOT NULL CHECK (total_score >= 0),
    max_possible_score FLOAT NOT NULL CHECK (max_possible_score > 0),
    percentage FLOAT NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    passed BIT NOT NULL,
    
    -- AI Analysis Metrics
    semantic_similarity FLOAT NOT NULL CHECK (semantic_similarity >= 0 AND semantic_similarity <= 1),
    coherence_score FLOAT NOT NULL CHECK (coherence_score >= 0 AND coherence_score <= 1),
    completeness_score FLOAT NOT NULL CHECK (completeness_score >= 0 AND completeness_score <= 1),
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Feedback
    detailed_feedback NTEXT NOT NULL,
    strengths NTEXT, -- JSON array
    weaknesses NTEXT, -- JSON array
    suggestions NTEXT, -- JSON array
    
    -- Metadata
    grading_model NVARCHAR(100) NOT NULL,
    processing_time_ms FLOAT,
    graded_at DATETIME2 DEFAULT GETUTCDATE(),
    graded_by NVARCHAR(100) DEFAULT 'ai_examiner',
    
    -- Additional JSON data for complex structures
    raw_llm_response NTEXT, -- Store the full LLM response
    criteria_scores NTEXT, -- JSON of individual criteria scores
    
    FOREIGN KEY (student_answer_id) REFERENCES student_answers(id) ON DELETE CASCADE
);

-- Evaluation of individual key concepts in student answers
CREATE TABLE concept_evaluations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    grading_result_id INT NOT NULL,
    key_concept_id INT NOT NULL,
    
    -- Evaluation Results
    present BIT NOT NULL,
    accuracy_score FLOAT NOT NULL CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    points_awarded FLOAT NOT NULL CHECK (points_awarded >= 0),
    points_possible FLOAT NOT NULL CHECK (points_possible >= 0),
    
    -- Evidence and Reasoning
    explanation NTEXT NOT NULL,
    evidence_text NTEXT, -- Quote from student answer
    reasoning NTEXT, -- Why this score was awarded
    
    -- Metadata
    evaluated_at DATETIME2 DEFAULT GETUTCDATE(),
    
    FOREIGN KEY (grading_result_id) REFERENCES grading_results(id) ON DELETE CASCADE,
    FOREIGN KEY (key_concept_id) REFERENCES key_concepts(id) ON DELETE CASCADE
);

-- Track grading sessions and batches
CREATE TABLE grading_sessions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(255) NOT NULL UNIQUE DEFAULT NEWID(),
    batch_name NVARCHAR(255),
    total_answers INT DEFAULT 0,
    completed_answers INT DEFAULT 0,
    failed_answers INT DEFAULT 0,
    
    -- Session Metadata
    started_at DATETIME2 DEFAULT GETUTCDATE(),
    completed_at DATETIME2,
    total_processing_time_ms FLOAT,
    average_score FLOAT,
    
    -- Configuration used
    llm_provider NVARCHAR(50),
    llm_model NVARCHAR(100),
    grading_temperature FLOAT,
    
    -- Status
    status NVARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed'))
);

-- Audit log for all system operations
CREATE TABLE audit_logs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    log_id NVARCHAR(255) NOT NULL UNIQUE DEFAULT NEWID(),
    
    -- Event Details
    event_type NVARCHAR(100) NOT NULL, -- grading, concept_extraction, etc.
    entity_type NVARCHAR(100), -- question, student_answer, grading_result
    entity_id NVARCHAR(255),
    
    -- Event Data
    event_data NTEXT, -- JSON data
    result_status NVARCHAR(20) CHECK (result_status IN ('success', 'failure', 'warning')),
    error_message NTEXT,
    
    -- Metadata
    user_id NVARCHAR(255),
    ip_address NVARCHAR(45),
    user_agent NVARCHAR(500),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    processing_time_ms FLOAT
);

-- =============================================
-- CREATE INDEXES FOR PERFORMANCE
-- =============================================

-- Questions table indexes
CREATE NONCLUSTERED INDEX IX_questions_question_id ON questions(question_id);
CREATE NONCLUSTERED INDEX IX_questions_subject ON questions(subject);
CREATE NONCLUSTERED INDEX IX_questions_topic ON questions(topic);
CREATE NONCLUSTERED INDEX IX_questions_created_at ON questions(created_at);

-- Key concepts indexes
CREATE NONCLUSTERED INDEX IX_key_concepts_question_id ON key_concepts(question_id);
CREATE NONCLUSTERED INDEX IX_key_concepts_importance_score ON key_concepts(importance_score DESC);

-- Rubric criteria indexes
CREATE NONCLUSTERED INDEX IX_rubric_criteria_question_id ON rubric_criteria(question_id);

-- Student answers indexes
CREATE NONCLUSTERED INDEX IX_student_answers_answer_id ON student_answers(answer_id);
CREATE NONCLUSTERED INDEX IX_student_answers_student_id ON student_answers(student_id);
CREATE NONCLUSTERED INDEX IX_student_answers_question_id ON student_answers(question_id);
CREATE NONCLUSTERED INDEX IX_student_answers_submitted_at ON student_answers(submitted_at DESC);

-- Grading results indexes
CREATE NONCLUSTERED INDEX IX_grading_results_result_id ON grading_results(result_id);
CREATE NONCLUSTERED INDEX IX_grading_results_student_answer_id ON grading_results(student_answer_id);
CREATE NONCLUSTERED INDEX IX_grading_results_percentage ON grading_results(percentage DESC);
CREATE NONCLUSTERED INDEX IX_grading_results_graded_at ON grading_results(graded_at DESC);
CREATE NONCLUSTERED INDEX IX_grading_results_passed ON grading_results(passed);

-- Concept evaluations indexes
CREATE NONCLUSTERED INDEX IX_concept_evaluations_grading_result_id ON concept_evaluations(grading_result_id);
CREATE NONCLUSTERED INDEX IX_concept_evaluations_key_concept_id ON concept_evaluations(key_concept_id);

-- Grading sessions indexes
CREATE NONCLUSTERED INDEX IX_grading_sessions_session_id ON grading_sessions(session_id);
CREATE NONCLUSTERED INDEX IX_grading_sessions_started_at ON grading_sessions(started_at DESC);
CREATE NONCLUSTERED INDEX IX_grading_sessions_status ON grading_sessions(status);

-- Audit logs indexes
CREATE NONCLUSTERED INDEX IX_audit_logs_log_id ON audit_logs(log_id);
CREATE NONCLUSTERED INDEX IX_audit_logs_event_type ON audit_logs(event_type);
CREATE NONCLUSTERED INDEX IX_audit_logs_entity_type ON audit_logs(entity_type);
CREATE NONCLUSTERED INDEX IX_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE NONCLUSTERED INDEX IX_audit_logs_result_status ON audit_logs(result_status);

-- =============================================
-- CREATE TRIGGERS FOR AUDIT LOGGING
-- =============================================

-- =============================================
-- CREATE TRIGGERS FOR AUDIT LOGGING
-- =============================================
GO

-- Trigger for updating updated_at timestamp on questions
CREATE TRIGGER TR_questions_updated_at
ON questions
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE questions 
    SET updated_at = GETUTCDATE()
    FROM questions q
    INNER JOIN inserted i ON q.id = i.id;
END;
GO

-- =============================================
-- CREATE STORED PROCEDURES
-- =============================================

-- Procedure to get question with all related data
CREATE PROCEDURE sp_GetQuestionComplete
    @QuestionId NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Main question data
    SELECT * FROM questions WHERE question_id = @QuestionId;
    
    -- Key concepts
    SELECT * FROM key_concepts WHERE question_id = (
        SELECT id FROM questions WHERE question_id = @QuestionId
    );
    
    -- Rubric criteria
    SELECT * FROM rubric_criteria WHERE question_id = (
        SELECT id FROM questions WHERE question_id = @QuestionId
    );
END;
GO

-- Procedure to get grading statistics
CREATE PROCEDURE sp_GetGradingStatistics
    @FromDate DATETIME2 = NULL,
    @ToDate DATETIME2 = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    IF @FromDate IS NULL SET @FromDate = DATEADD(day, -30, GETUTCDATE());
    IF @ToDate IS NULL SET @ToDate = GETUTCDATE();
    
    SELECT 
        COUNT(*) AS total_gradings,
        AVG(percentage) AS average_percentage,
        MIN(percentage) AS min_percentage,
        MAX(percentage) AS max_percentage,
        SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) AS total_passed,
        AVG(processing_time_ms) AS avg_processing_time_ms,
        AVG(semantic_similarity) AS avg_semantic_similarity,
        AVG(coherence_score) AS avg_coherence_score,
        AVG(completeness_score) AS avg_completeness_score,
        AVG(confidence_score) AS avg_confidence_score
    FROM grading_results 
    WHERE graded_at BETWEEN @FromDate AND @ToDate;
END;
GO

-- Procedure to clean old audit logs
CREATE PROCEDURE sp_CleanOldAuditLogs
    @DaysToKeep INT = 90
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CutoffDate DATETIME2 = DATEADD(day, -@DaysToKeep, GETUTCDATE());
    
    DELETE FROM audit_logs 
    WHERE created_at < @CutoffDate;
    
    SELECT @@ROWCOUNT AS rows_deleted;
END;
GO

-- =============================================
-- INSERT SAMPLE DATA
-- =============================================

-- Sample questions
INSERT INTO questions (question_id, subject, topic, question_text, ideal_answer, max_marks, passing_threshold, difficulty_level)
VALUES 
('PHYS_001', 'Physics', 'Newton''s Laws of Motion', 
 'Explain Newton''s three laws of motion and provide examples for each law.',
 'Newton''s First Law (Law of Inertia): An object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an unbalanced force. Example: A ball rolling on a frictionless surface will continue rolling indefinitely. Newton''s Second Law: The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass (F = ma). Example: Pushing a heavy box requires more force than pushing a light box to achieve the same acceleration. Newton''s Third Law: For every action, there is an equal and opposite reaction. Example: When you walk, you push backward on the ground, and the ground pushes forward on you.',
 100.0, 60.0, 'intermediate'),

('HIST_001', 'History', 'World War II', 
 'Discuss the main causes of World War II and their interconnections.',
 'The main causes of World War II were: 1) The Treaty of Versailles created resentment in Germany through harsh terms and reparations. 2) Economic instability from the Great Depression led to political extremism. 3) The rise of totalitarian regimes (Nazi Germany, Fascist Italy, Imperial Japan) with aggressive expansionist policies. 4) The failure of the League of Nations to maintain peace and prevent aggression. 5) The policy of appeasement by Western democracies encouraged further aggression. These causes were interconnected - economic hardship led to extremist governments, which pursued aggressive policies that the international community failed to stop effectively.',
 100.0, 65.0, 'intermediate');

-- Sample key concepts for Physics question
DECLARE @PhysicsQuestionId INT = (SELECT id FROM questions WHERE question_id = 'PHYS_001');

INSERT INTO key_concepts (question_id, concept_name, concept_description, importance_score, keywords, max_points)
VALUES 
(@PhysicsQuestionId, 'Newton''s First Law', 'Understanding of the law of inertia and its implications', 0.9, '["inertia", "rest", "motion", "force", "velocity"]', 30.0),
(@PhysicsQuestionId, 'Newton''s Second Law', 'Understanding of F=ma relationship', 0.95, '["force", "mass", "acceleration", "F=ma", "proportional"]', 35.0),
(@PhysicsQuestionId, 'Newton''s Third Law', 'Understanding of action-reaction pairs', 0.9, '["action", "reaction", "equal", "opposite", "pairs"]', 30.0),
(@PhysicsQuestionId, 'Examples', 'Providing relevant examples for each law', 0.3, '["examples", "real-world", "applications"]', 5.0);

-- Sample rubric criteria for Physics question
INSERT INTO rubric_criteria (question_id, criteria_name, criteria_description, max_points, weight)
VALUES 
(@PhysicsQuestionId, 'Conceptual Understanding', 'Demonstrates clear understanding of the three laws', 60.0, 0.6),
(@PhysicsQuestionId, 'Examples and Applications', 'Provides relevant and accurate examples', 25.0, 0.25),
(@PhysicsQuestionId, 'Clarity and Organization', 'Answer is well-organized and clearly written', 15.0, 0.15);

-- Sample key concepts for History question
DECLARE @HistoryQuestionId INT = (SELECT id FROM questions WHERE question_id = 'HIST_001');

INSERT INTO key_concepts (question_id, concept_name, concept_description, importance_score, keywords, max_points)
VALUES 
(@HistoryQuestionId, 'Treaty of Versailles Impact', 'Understanding how the treaty created conditions for war', 0.85, '["Versailles", "reparations", "resentment", "Germany"]', 20.0),
(@HistoryQuestionId, 'Economic Factors', 'Role of Great Depression and economic instability', 0.8, '["Great Depression", "economic", "instability", "unemployment"]', 20.0),
(@HistoryQuestionId, 'Rise of Totalitarianism', 'Understanding emergence of extremist regimes', 0.9, '["totalitarian", "Nazi", "Fascist", "extremism", "dictators"]', 25.0),
(@HistoryQuestionId, 'Failed Diplomacy', 'League of Nations failure and appeasement policy', 0.75, '["League of Nations", "appeasement", "diplomacy", "failure"]', 20.0),
(@HistoryQuestionId, 'Interconnections', 'Explaining how causes were related', 0.7, '["interconnected", "related", "caused", "led to"]', 15.0);

-- Sample rubric criteria for History question
INSERT INTO rubric_criteria (question_id, criteria_name, criteria_description, max_points, weight)
VALUES 
(@HistoryQuestionId, 'Historical Knowledge', 'Demonstrates knowledge of key historical facts and events', 50.0, 0.5),
(@HistoryQuestionId, 'Analysis and Synthesis', 'Shows ability to analyze and connect different causes', 30.0, 0.3),
(@HistoryQuestionId, 'Communication', 'Clear and coherent presentation of ideas', 20.0, 0.2);

-- =============================================
-- CREATE VIEWS FOR COMMON QUERIES
-- =============================================

GO

-- View for question summary with statistics
CREATE VIEW vw_QuestionSummary AS
SELECT 
    q.id,
    q.question_id,
    q.subject,
    q.topic,
    q.max_marks,
    q.difficulty_level,
    COUNT(DISTINCT kc.id) AS key_concepts_count,
    COUNT(DISTINCT rc.id) AS rubric_criteria_count,
    COUNT(DISTINCT sa.id) AS student_answers_count,
    AVG(gr.percentage) AS avg_score,
    q.created_at,
    q.updated_at
FROM questions q
LEFT JOIN key_concepts kc ON q.id = kc.question_id
LEFT JOIN rubric_criteria rc ON q.id = rc.question_id
LEFT JOIN student_answers sa ON q.id = sa.question_id
LEFT JOIN grading_results gr ON sa.id = gr.student_answer_id
GROUP BY q.id, q.question_id, q.subject, q.topic, q.max_marks, q.difficulty_level, q.created_at, q.updated_at;
GO

GO

-- View for grading performance metrics
CREATE VIEW vw_GradingPerformance AS
SELECT 
    sa.student_id,
    q.subject,
    q.topic,
    q.difficulty_level,
    gr.percentage,
    gr.passed,
    gr.semantic_similarity,
    gr.coherence_score,
    gr.completeness_score,
    gr.confidence_score,
    gr.grading_model,
    gr.processing_time_ms,
    gr.graded_at
FROM grading_results gr
JOIN student_answers sa ON gr.student_answer_id = sa.id
JOIN questions q ON sa.question_id = q.id;
GO

-- =============================================
-- GRANT PERMISSIONS (adjust as needed)
-- =============================================

-- Create application user (uncomment and modify as needed)
-- CREATE LOGIN ai_examiner_app WITH PASSWORD = 'YourSecurePassword123!';
-- CREATE USER ai_examiner_user FOR LOGIN ai_examiner_app;

-- Grant permissions to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON questions TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON key_concepts TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rubric_criteria TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON student_answers TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON grading_results TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON concept_evaluations TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON grading_sessions TO ai_examiner_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON audit_logs TO ai_examiner_user;
-- GRANT EXECUTE ON sp_GetQuestionComplete TO ai_examiner_user;
-- GRANT EXECUTE ON sp_GetGradingStatistics TO ai_examiner_user;
-- GRANT SELECT ON vw_QuestionSummary TO ai_examiner_user;
-- GRANT SELECT ON vw_GradingPerformance TO ai_examiner_user;

PRINT 'Database setup completed successfully!';
PRINT 'Tables created: questions, key_concepts, rubric_criteria, student_answers, grading_results, concept_evaluations, grading_sessions, audit_logs';
PRINT 'Indexes, triggers, stored procedures, and views created.';
PRINT 'Sample data inserted for testing.';
GO