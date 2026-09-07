import unittest

from src.build_graph import build_graph, prepare_entries


class BuildGraphTest(unittest.TestCase):
    def setUp(self):
        self.lexicon = prepare_entries([
            {"term": "pain", "type": "Symptom", "canonical": "pain", "source": "manual"},
            {"term": "aspirin", "type": "Treatment", "canonical": "aspirin", "source": "manual"},
            {"term": "pantoprazole", "type": "Treatment", "canonical": "pantoprazole", "source": "manual"},
            {"term": "prednisone", "type": "Treatment", "canonical": "prednisone", "source": "manual"},
            {"term": "diltiazem", "type": "Treatment", "canonical": "diltiazem", "source": "manual"},
            {"term": "CAS", "type": "Condition", "canonical": "coronary artery spasm", "source": "manual"},
            {"term": "computed tomography", "type": "Exam", "canonical": "computed tomography", "source": "manual"},
            {"term": "CT", "type": "Exam", "canonical": "computed tomography", "source": "manual"},
            {"term": "CAG", "type": "Exam", "canonical": "coronary angiography", "source": "manual"},
            {"term": "ECG", "type": "Exam", "canonical": "electrocardiogram", "source": "manual"},
            {"term": "acute coronary syndrome", "type": "Condition", "canonical": "acute coronary syndrome", "source": "manual"},
            {"term": "hypertension", "type": "Condition", "canonical": "hypertension", "source": "manual"},
        ], "term")
        self.triggers = prepare_entries([
            {"phrase": "presented with", "kind": "relation", "value": "HAS_SYMPTOM"},
            {"phrase": "treated with", "kind": "relation", "value": "RECEIVED_TREATMENT"},
            {"phrase": "no", "kind": "negation", "value": "NEGATED"},
            {"phrase": "possible", "kind": "uncertainty", "value": "SUSPECTED"},
            {"phrase": "cannot be excluded", "kind": "uncertainty", "value": "SUSPECTED"},
            {"phrase": "resolution of", "kind": "resolution", "value": "RESOLVED"},
            {"phrase": "was suggested", "kind": "not_performed", "value": "NOT_PERFORMED"},
            {"phrase": "was refused", "kind": "not_performed", "value": "NOT_PERFORMED"},
        ], "phrase")

    def test_creates_case_entity_nodes_and_edges(self):
        cases = [{
            "case_id": "c1", "article_id": "a1", "age": "44", "gender": "female",
            "title": "Example", "case_text": "Presented with pain. Two days later, treated with aspirin 500 mg.",
        }]
        nodes, edges = build_graph(cases, self.lexicon, self.triggers)
        self.assertEqual([n["type"] for n in nodes], ["Case", "Symptom", "Treatment"])
        self.assertIn("dose", nodes[-1]["attributes"])
        self.assertIn("time", nodes[-1]["attributes"])
        self.assertIn("BEFORE", [edge["relation"] for edge in edges])

    def test_negated_entity_is_not_added(self):
        cases = [{
            "case_id": "c1", "article_id": "a1", "age": "", "gender": "",
            "title": "", "case_text": "The patient had no pain.",
        }]
        nodes, edges = build_graph(cases, self.lexicon, self.triggers)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(edges, [])

    def test_name_and_nearby_abbreviation_create_one_node(self):
        cases = [{
            "case_id": "c1", "case_text": "Computed tomography (CT) was performed."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        self.assertEqual([node["type"] for node in nodes].count("Exam"), 1)

    def test_dose_is_attached_only_to_nearby_treatment(self):
        cases = [{
            "case_id": "c1",
            "case_text": "Pantoprazole (40 mg) was used to prevent injury caused by prednisone."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        treatments = {node["label"]: node["attributes"] for node in nodes if node["type"] == "Treatment"}
        self.assertEqual(treatments["pantoprazole"]["dose"], "40 mg")
        self.assertNotIn("dose", treatments["prednisone"])

    def test_uncertainty_does_not_cross_comma(self):
        cases = [{
            "case_id": "c1",
            "case_text": "With a possible diagnosis of CAS, 5 mg of diltiazem was administered."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        assertions = {node["label"]: node["attributes"]["assertion"] for node in nodes if node["type"] != "Case"}
        self.assertEqual(assertions["coronary artery spasm"], "suspected")
        self.assertEqual(assertions["diltiazem"], "affirmed")

    def test_resolved_and_refused_mentions_are_not_facts(self):
        cases = [{
            "case_id": "c1",
            "case_text": "There was complete resolution of pain. CAG was suggested but was refused."
        }]
        nodes, edges = build_graph(cases, self.lexicon, self.triggers)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(edges, [])

    def test_condition_of_other_person_is_not_added(self):
        cases = [{
            "case_id": "c1", "case_text": "The patient's mother had hypertension."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        self.assertEqual(len(nodes), 1)

    def test_before_expression_does_not_create_forward_edge(self):
        cases = [{
            "case_id": "c1", "case_text": "The patient had pain. CT before admission was normal."
        }]
        _, edges = build_graph(cases, self.lexicon, self.triggers)
        self.assertNotIn("BEFORE", [edge["relation"] for edge in edges])

    def test_uncertainty_can_follow_condition(self):
        cases = [{
            "case_id": "c1",
            "case_text": "Acute coronary syndrome cannot be excluded."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        condition = next(node for node in nodes if node["type"] == "Condition")
        self.assertEqual(condition["attributes"]["assertion"], "suspected")

    def test_measurement_is_not_attached_to_unrelated_exam(self):
        cases = [{
            "case_id": "c1", "case_text": "Troponin was 0.031 ng/mL and ECG was normal."
        }]
        nodes, _ = build_graph(cases, self.lexicon, self.triggers)
        exam = next(node for node in nodes if node["type"] == "Exam")
        self.assertNotIn("measurement", exam["attributes"])


if __name__ == "__main__":
    unittest.main()
