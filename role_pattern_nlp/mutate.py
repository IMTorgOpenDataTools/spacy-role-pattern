from pprint import pprint
import spacy_pattern_builder
from role_pattern_nlp import role_pattern_builder
from role_pattern_nlp.role_pattern import RolePattern
from role_pattern_nlp.match import RolePatternMatch
from role_pattern_nlp import util


def pattern_fitness(pattern, matches, pos_matches, neg_matches):
    true_pos = [m for m in pos_matches if m in matches]
    true_neg = [m for m in neg_matches if m not in matches]
    n_true_pos = len(true_pos)
    n_true_neg = len(true_neg)
    n_pos_matches = len(pos_matches)
    n_neg_matches = len(neg_matches)
    pos_score = n_true_pos / n_pos_matches  if n_pos_matches > 0 else 1
    neg_score = n_true_neg / n_neg_matches  if n_neg_matches > 0 else 1    
    pos_score_weighted = pos_score * 0.5
    neg_score_weighted = neg_score * 0.5
    fitness_score = pos_score_weighted + neg_score_weighted
    return {
        'score': fitness_score,
        'pos_score': pos_score,
        'neg_score': neg_score,
        'true_pos': true_pos,
        'true_neg': true_neg,
    }


def yield_node_level_pattern_variants(role_pattern, training_match, feature_dicts):
    spacy_dependency_pattern = role_pattern.spacy_dep_pattern
    match_token_labels = role_pattern.token_labels
    match_tokens = training_match.match_tokens
    nonlabelled_tokens = [
        token for token, label in zip(match_tokens, match_token_labels) if label
    ]
    # First mutate only the non-labelled match tokens
    dependency_pattern_variants = list(
        spacy_pattern_builder.yield_node_level_pattern_variants(
            spacy_dependency_pattern,
            match_tokens,
            feature_dicts,
            mutate_tokens=nonlabelled_tokens,
        )
    )
    # Then all variants
    dependency_pattern_variants += list(
        spacy_pattern_builder.yield_node_level_pattern_variants(
            spacy_dependency_pattern, match_tokens, feature_dicts
        )
    )
    dependency_pattern_variants = util.unique_list(dependency_pattern_variants)
    for dependency_pattern_variant in dependency_pattern_variants:
        assert len(dependency_pattern_variant) == len(spacy_dependency_pattern)
        role_pattern_variant = RolePattern(
            dependency_pattern_variant, match_token_labels
        )
        role_pattern_variant.token_labels_depth_order = (
            role_pattern.token_labels_depth_order
        )
        role_pattern_variant.training_match = training_match
        yield role_pattern_variant


def yield_tree_level_pattern_variants(role_pattern, training_match, feature_dict):
    match_tokens = training_match.match_tokens
    extended_match_tokens = spacy_pattern_builder.yield_extended_trees(match_tokens)
    doc = util.doc_from_match(training_match)
    for match_tokens in extended_match_tokens:
        match_tokens = sorted(match_tokens, key=lambda token: token.i)
        token_labels = role_pattern_builder.build_pattern_label_list(
            match_tokens, training_match
        )
        dependency_pattern_variant = spacy_pattern_builder.build_dependency_pattern(
            doc, match_tokens, feature_dict=feature_dict
        )
        assert (
            len(dependency_pattern_variant) == len(role_pattern.spacy_dep_pattern) + 1
        )
        assert len(token_labels) == len(role_pattern.token_labels) + 1
        role_pattern_variant = RolePattern(dependency_pattern_variant, token_labels)
        match_tokens_depth_order = spacy_pattern_builder.util.sort_by_depth(
            match_tokens
        )  # Should be same order as the dependency pattern
        token_labels_depth_order = role_pattern_builder.build_pattern_label_list(
            match_tokens_depth_order, training_match
        )
        role_pattern_variant.token_labels_depth_order = token_labels_depth_order
        role_pattern_variant.builder = role_pattern.builder
        new_training_match = RolePatternMatch(training_match)
        new_training_match.match_tokens = match_tokens
        role_pattern_variant.training_match = new_training_match
        yield role_pattern_variant
