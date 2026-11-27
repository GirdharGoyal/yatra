from backend.assistant.rag import policy_retriever

RAG_TEST_SET = [
    {"q": "24 ghante pehle cancel karne par kitna refund milega?", "expected_doc": "cancellation_policy.md"},
    {"q": "24 hours ke andar cancel karne par kitni fee lagti hai?", "expected_doc": "cancellation_policy.md"},
    {"q": "No-show par refund milta hai kya?", "expected_doc": "cancellation_policy.md"},
    {"q": "Refund bank account mein kitne din mein aata hai?", "expected_doc": "refund_policy.md"},
    {"q": "Pending payment booking cancel karne par kya hota hai?", "expected_doc": "refund_policy.md"},
    {"q": "Cabin baggage ka weight limit kya hai?", "expected_doc": "baggage_policy.md"},
    {"q": "Check-in baggage kitna kg free hai aur extra charge kya hai?", "expected_doc": "baggage_policy.md"},
    {"q": "Kaun se payment methods accepted hain?", "expected_doc": "payment_policy.md"},
    {"q": "Double click karne par do baar paisa toh nahi katega?", "expected_doc": "payment_policy.md"},
    {"q": "Ticket receipt kaise download kar sakte hain?", "expected_doc": "faq.md"},
]


def run_rag_eval(top_k: int = 3):
    hits = 0
    total_precision = 0.0

    print(f"{'Question':<55} | {'Expected Doc':<24} | {'Hit?'}")
    print("-" * 92)

    for item in RAG_TEST_SET:
        results = policy_retriever.search(item["q"], top_k=top_k)
        retrieved_docs = [r["source"] for r in results]
        hit = item["expected_doc"] in retrieved_docs
        if hit:
            hits += 1
        prec = retrieved_docs.count(item["expected_doc"]) / max(1, len(retrieved_docs))
        total_precision += prec
        print(f"{item['q'][:53]:<55} | {item['expected_doc']:<24} | {'✅' if hit else '❌'}")

    recall = (hits / len(RAG_TEST_SET)) * 100
    avg_precision = (total_precision / len(RAG_TEST_SET)) * 100
    print("-" * 92)
    print(f"Summary (top_k={top_k}) -> Context Recall: {recall:.1f}% | Context Precision: {avg_precision:.1f}%")


if __name__ == "__main__":
    run_rag_eval(top_k=3)