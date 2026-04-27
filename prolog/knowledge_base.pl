%% ============================================================
%% AI Teaching Agent Team — Prolog Knowledge Base
%% Provides prerequisite relationships and answer validation rules.
%% Keep this file SMALL and CLEAN.
%% ============================================================

%% ---------- prerequisite/2 ----------
%% prerequisite(X, Y) means X must be learned BEFORE Y.

% Mathematics chain
prerequisite(algebra, calculus).
prerequisite(calculus, differential_equations).
prerequisite(calculus, linear_algebra).
prerequisite(calculus, probability).
prerequisite(probability, statistics).
prerequisite(logic, discrete_mathematics).
prerequisite(discrete_mathematics, algorithms).

% Computer Science chain
prerequisite(programming_basics, data_structures).
prerequisite(data_structures, algorithms).
prerequisite(algorithms, dynamic_programming).
prerequisite(programming_basics, object_oriented_programming).
prerequisite(programming_basics, databases).
prerequisite(databases, web_development).
prerequisite(programming_basics, web_development).

% AI / ML chain
prerequisite(linear_algebra, machine_learning).
prerequisite(statistics, machine_learning).
prerequisite(machine_learning, deep_learning).
prerequisite(linear_algebra, deep_learning).
prerequisite(statistics, data_science).
prerequisite(programming_basics, data_science).

%% ---------- prerequisite_chain/2 ----------
%% Transitive closure — checks indirect prerequisites.

prerequisite_chain(X, Y) :- prerequisite(X, Y).
prerequisite_chain(X, Y) :- prerequisite(X, Z), prerequisite_chain(Z, Y).

%% ---------- can_learn/2 ----------
%% can_learn(Known, Target) — knowing Known contributes toward Target.

can_learn(Known, Target) :- prerequisite_chain(Known, Target).

%% ---------- valid_answer_type/2 ----------
%% valid_answer_type(ProblemType, RequiredStep)
%% Maps problem domains to expected solution components.

valid_answer_type(calculus, show_differentiation).
valid_answer_type(calculus, show_integration).
valid_answer_type(calculus, verify_boundary_conditions).
valid_answer_type(algebra, isolate_variables).
valid_answer_type(algebra, simplify_equations).
valid_answer_type(statistics, apply_formula).
valid_answer_type(statistics, interpret_results).
valid_answer_type(programming, explain_logic).
valid_answer_type(programming, analyze_complexity).
valid_answer_type(machine_learning, justify_model_selection).
valid_answer_type(machine_learning, define_evaluation_metrics).
valid_answer_type(physics, draw_free_body_diagram).
valid_answer_type(physics, verify_units).
valid_answer_type(data_structures, explain_structure_choice).
valid_answer_type(data_structures, analyze_complexity).
valid_answer_type(algorithms, show_step_trace).
valid_answer_type(algorithms, prove_correctness).

%% ---------- topic_difficulty/2 ----------
%% topic_difficulty(Topic, Level)

topic_difficulty(algebra, beginner).
topic_difficulty(programming_basics, beginner).
topic_difficulty(logic, beginner).
topic_difficulty(calculus, intermediate).
topic_difficulty(data_structures, intermediate).
topic_difficulty(statistics, intermediate).
topic_difficulty(linear_algebra, intermediate).
topic_difficulty(probability, intermediate).
topic_difficulty(discrete_mathematics, intermediate).
topic_difficulty(object_oriented_programming, intermediate).
topic_difficulty(databases, intermediate).
topic_difficulty(algorithms, advanced).
topic_difficulty(machine_learning, advanced).
topic_difficulty(deep_learning, advanced).
topic_difficulty(dynamic_programming, advanced).
topic_difficulty(differential_equations, advanced).
topic_difficulty(data_science, advanced).
topic_difficulty(web_development, intermediate).
