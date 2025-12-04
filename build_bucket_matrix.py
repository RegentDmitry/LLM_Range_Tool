#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build bucket matrices from range CSV files

Process:
1. Load CSV with ranges (combo, weight, ev)
2. Bucket each combo via get_all_buckets()
3. Aggregate into matrix: buckets x actions
4. Build decision tree with min_leaf parameter
5. Export to Mermaid format
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
from sklearn.tree import DecisionTreeClassifier
import json
import sys

# Add path to lib for direct module import
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

import card
import buckets

Card = card.Card
get_all_buckets = buckets.get_all_buckets

# Bucket names mapping (85 features in order)
BUCKET_NAMES = [
    'flush_royal', 'flush', 'nut_flush', 'nut_flush2', 'not_nut_flush',
    'flush_draw', 'not_nut_flush_draw', 'nut_flush_draw', 'nut_flush_draw2',
    'set', 'top_set', 'middle_set', 'bottom_set', 'two_sets',
    'trips', 'quads', 'full_house', 'full_house_nut', 'full_house_not_nut',
    'pocket_pair', 'pair', 'top_pair', 'middle_pair', 'bottom_pair',
    'tp_tk', 'two_pairs', 'top_two_pairs', 'top_and_bottom_pairs', 'bottom_two_pairs',
    'three_pairs', 'over_pair', 'two_over_pairs',
    'straight_flush', 'straight_nut', 'straight_nut2', 'straight_nut3', 'straight',
    'straight_draw', 'no_draw', 'backdoor_straight_draw', 'backdoor_straight_draw4',
    'bdfd', 'bdfd1', 'bdfd2', 'bdfd_nut',
    'gutshot', 'oesd', 'wrap', 'wrap9', 'wrap12', 'wrap13',
    'minor_wrap', 'wrap16', 'wrap17', 'wrap20', 'major_wrap',
    'flush_blocker', 'flush_blocker_nut', 'flush_blocker_nut2',
    'flush_draw_blocker', 'flush_draw_blocker_nut', 'flush_draw_blocker1',
    'flush_draw_blocker2', 'flush_draw_blocker_nut2',
    'straight_blocker', 'straight_blocker1', 'straight_blocker2',
    'straight_blocker3', 'straight_blocker4',
    'straight_blocker_nut', 'straight_blocker_nut1', 'straight_blocker_nut2',
    'straight_blocker_nut3', 'straight_blocker_nut4',
    'straight_draw_blocker', 'straight_draw_blocker1', 'straight_draw_blocker2',
    'straight_draw_blocker3', 'straight_draw_blocker4',
    'straight_draw_blocker_nut', 'straight_draw_blocker_nut1',
    'straight_draw_blocker_nut2', 'straight_draw_blocker_nut3',
    'straight_draw_blocker_nut4'
]


def parse_combo(combo_str: str) -> List[Card]:
    """Parse combo string into 4 cards for PLO4"""
    if len(combo_str) != 8:
        raise ValueError(f"Invalid combo length: {combo_str}")

    cards = Card.parse_cards(combo_str)

    if len(cards) != 4:
        raise ValueError(f"Expected 4 cards, got {len(cards)}")

    return cards


def load_range_csv(csv_path: str, board: str) -> pd.DataFrame:
    """
    Load CSV with range and add buckets

    Args:
        csv_path: Path to CSV file (combo, weight, ev)
        board: Board string (e.g. "9s6d5c")

    Returns:
        DataFrame with columns: combo, weight, ev, flush_royal, flush, ..., straight_draw_blocker_nut4
    """
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} combos from {csv_path}")

    bucket_data = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Bucketing"):
        combo_str = row['combo']

        try:
            # Get buckets (85 elements)
            # get_all_buckets accepts strings, parses them internally
            buckets_result = get_all_buckets(combo_str, board)

            # Form row with data
            bucket_row = {
                'combo': combo_str,
                'weight': row['weight'],
                'ev': row['ev']
            }

            # Add buckets with readable names
            for i, bucket_value in enumerate(buckets_result):
                bucket_row[BUCKET_NAMES[i]] = int(bucket_value)

            bucket_data.append(bucket_row)

        except Exception as e:
            print(f"Error processing {combo_str}: {e}")
            continue

    df_buckets = pd.DataFrame(bucket_data)

    print(f"Processed {len(df_buckets)} combos with buckets")

    return df_buckets


def combine_ranges(range_files: Dict[str, str], board: str) -> pd.DataFrame:
    """
    Combine multiple CSV files with different actions

    Args:
        range_files: Dict {action_name: csv_path}
        board: Board string (e.g. "9s6d5c")

    Returns:
        DataFrame with columns: combo, action, weight, ev, flush_royal, ..., straight_draw_blocker_nut4
    """
    all_data = []

    for action_name, csv_path in range_files.items():
        print(f"\nLoading {action_name} from {csv_path}")

        df = load_range_csv(csv_path, board)
        df['action'] = action_name

        all_data.append(df)

    # Combine all actions
    df_combined = pd.concat(all_data, ignore_index=True)

    print(f"\nTotal rows after combining: {len(df_combined)}")
    print(f"Actions: {df_combined['action'].value_counts().to_dict()}")

    return df_combined


def build_bucket_matrix(df_combined: pd.DataFrame) -> pd.DataFrame:
    """
    Build bucket matrix by aggregating by buckets

    Args:
        df_combined: DataFrame with combo, action, weight, ev, buckets

    Returns:
        Matrix: bucket features x actions (with percentages)
    """
    # Bucket columns (readable names)
    bucket_columns = BUCKET_NAMES

    print(f"\nBucket features: {len(bucket_columns)}")

    # Group by buckets and actions
    df_grouped = df_combined.groupby(bucket_columns + ['action'], as_index=False).agg({
        'weight': 'sum',
        'ev': 'mean'
    })

    print(f"Unique bucket combinations after grouping: {len(df_grouped[bucket_columns].drop_duplicates())}")

    # Pivot to create matrix
    df_pivot = df_grouped.pivot_table(
        index=bucket_columns,
        columns='action',
        values='weight',
        fill_value=0
    ).reset_index()

    # Get list of actions
    actions = df_combined['action'].unique().tolist()

    # Ensure all action columns exist
    for action in actions:
        if action not in df_pivot.columns:
            df_pivot[action] = 0

    # Calculate total weight for each bucket
    df_pivot['total_weight'] = df_pivot[actions].sum(axis=1)

    # Normalize to percentages
    for action in actions:
        df_pivot[action] = (df_pivot[action] / df_pivot['total_weight'] * 100).fillna(0)

    # Round
    for action in actions:
        df_pivot[action] = df_pivot[action].round(2)

    df_pivot['total_weight'] = df_pivot['total_weight'].round(2)

    # Reorder columns
    final_columns = actions + ['total_weight'] + bucket_columns
    df_pivot = df_pivot[final_columns]

    df_pivot = df_pivot.sort_values(bucket_columns).reset_index(drop=True)

    print(f"\nMatrix created!")
    print(f"Buckets (unique combinations): {len(df_pivot)}")
    print(f"Columns: {len(df_pivot.columns)}")

    return df_pivot, actions


def tree_to_mermaid(tree, feature_names: List[str], class_names: List[str],
                    node: int = 0, node_id_prefix: str = 'node',
                    include_styles: bool = False) -> List[str]:
    """
    Convert sklearn tree to Mermaid flowchart format

    Args:
        tree: sklearn tree object (clf.tree_)
        feature_names: List of feature names (readable bucket names)
        class_names: List of class names (actions)
        node: Current node (for recursion)
        node_id_prefix: Prefix for node IDs
        include_styles: Add styles (colors)

    Returns:
        List of Mermaid diagram lines
    """
    lines = []
    node_id = f"{node_id_prefix}{node}"

    if tree.feature[node] == -2:  # Leaf node
        values = tree.value[node][0]
        total = sum(values)
        class_idx = values.argmax()
        class_name = class_names[class_idx]

        label = class_name

        # Add percentages if multiple classes
        percentages = []
        for i, value in enumerate(values):
            if value > 0:
                pct = (value / total) * 100
                percentages.append(f"{class_names[i]}: {pct:.1f}%")

        if len(percentages) > 1:
            label += "<br/>" + "<br/>".join(percentages)

        lines.append(f'    {node_id}["{label}"]')

        if include_styles:
            lines.append(f'    style {node_id} fill:#90EE90')

        return lines

    # Split node
    feature = feature_names[tree.feature[node]]
    threshold = tree.threshold[node]

    # Use readable feature name directly
    label = feature

    lines.append(f'    {node_id}{{"{label}"}}')

    # Process left subtree
    left_child = tree.children_left[node]
    left_node_id = f"{node_id_prefix}{left_child}"
    left_lines = tree_to_mermaid(tree, feature_names, class_names, left_child, node_id_prefix, include_styles)

    # For binary features: left = 0 (No), right = 1 (Yes)
    lines.append(f'    {node_id} -->|No| {left_node_id}')

    lines.extend(left_lines)

    # Process right subtree
    right_child = tree.children_right[node]
    right_node_id = f"{node_id_prefix}{right_child}"
    right_lines = tree_to_mermaid(tree, feature_names, class_names, right_child, node_id_prefix, include_styles)

    lines.append(f'    {node_id} -->|Yes| {right_node_id}')

    lines.extend(right_lines)

    return lines


def build_decision_tree(df_matrix: pd.DataFrame, actions: List[str],
                       min_leaf: int = 1) -> Tuple[DecisionTreeClassifier, List[str]]:
    """
    Build decision tree based on bucket matrix

    Args:
        df_matrix: Bucket matrix
        actions: List of actions
        min_leaf: Minimum samples in leaf (min_samples_leaf)

    Returns:
        (trained classifier, feature_columns)
    """
    # Define target variable - action with max percentage
    df_matrix['target'] = df_matrix[actions].idxmax(axis=1)

    print(f"\nTarget action distribution:")
    print(df_matrix['target'].value_counts())

    # Features - all bucket columns (readable names)
    feature_columns = BUCKET_NAMES

    print(f"\nFeatures: {len(feature_columns)}")

    X = df_matrix[feature_columns]
    y = df_matrix['target']
    weights = df_matrix['total_weight']

    # Train tree
    clf = DecisionTreeClassifier(
        min_samples_leaf=min_leaf,
        random_state=42
    )

    clf.fit(X, y, sample_weight=weights)

    print(f"\nTree trained:")
    print(f"  min_samples_leaf: {min_leaf}")
    print(f"  Depth: {clf.tree_.max_depth}")
    print(f"  Leaves: {clf.tree_.n_leaves}")
    print(f"  Nodes: {clf.tree_.node_count}")
    print(f"  Accuracy: {clf.score(X, y, sample_weight=weights):.2%}")

    return clf, feature_columns


def export_tree_to_mermaid(clf: DecisionTreeClassifier, feature_columns: List[str],
                           actions: List[str], output_path: str):
    """
    Export tree to Mermaid file

    Args:
        clf: Trained classifier
        feature_columns: List of feature names (readable bucket names)
        actions: List of actions (classes)
        output_path: Path to save .mmd file
    """
    # Generate Mermaid diagram
    mermaid_lines = ['flowchart TD']
    mermaid_lines.extend(tree_to_mermaid(
        clf.tree_,
        feature_columns,
        sorted(actions),
        include_styles=False
    ))

    mermaid_content = '\n'.join(mermaid_lines)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(mermaid_content)

    print(f"\nMermaid diagram saved: {output_path}")
    print(f"  Size: {len(mermaid_content)} characters")
    print(f"  Usage:")
    print(f"    1. GitHub/GitLab markdown: ```mermaid ... ```")
    print(f"    2. https://mermaid.live for preview")


def export_tree_metadata(clf: DecisionTreeClassifier, feature_columns: List[str],
                        actions: List[str], board: str, tree_type: str,
                        min_leaf: int, output_path: str):
    """
    Export tree metadata to JSON file

    Args:
        clf: Trained classifier
        feature_columns: List of feature names
        actions: List of actions
        board: Board string
        tree_type: 'lead' or 'nolead'
        min_leaf: min_samples_leaf parameter
        output_path: Path to save JSON file
    """
    tree = clf.tree_

    # Feature importance
    feature_importance = {}
    for i, feat in enumerate(feature_columns):
        importance = clf.feature_importances_[i]
        if importance > 0:
            feature_importance[feat] = round(float(importance), 4)

    # Sort by importance
    feature_importance = dict(sorted(feature_importance.items(),
                                    key=lambda x: x[1], reverse=True))

    # Leaf statistics
    leaf_stats = []
    for node_id in range(tree.node_count):
        if tree.feature[node_id] == -2:  # Leaf node
            values = tree.value[node_id][0]
            total = sum(values)
            class_idx = values.argmax()

            percentages = {}
            for i, action in enumerate(sorted(actions)):
                pct = (values[i] / total * 100) if total > 0 else 0
                if pct > 0:
                    percentages[action] = round(float(pct), 1)

            leaf_stats.append({
                'node_id': int(node_id),
                'samples': int(tree.n_node_samples[node_id]),
                'decision': sorted(actions)[class_idx],
                'percentages': percentages
            })

    # Node information
    nodes = []
    for node_id in range(tree.node_count):
        if tree.feature[node_id] != -2:  # Split node
            nodes.append({
                'node_id': int(node_id),
                'feature': feature_columns[tree.feature[node_id]],
                'threshold': round(float(tree.threshold[node_id]), 2),
                'samples': int(tree.n_node_samples[node_id]),
                'left_child': int(tree.children_left[node_id]),
                'right_child': int(tree.children_right[node_id])
            })

    # Metadata
    metadata = {
        'tree_type': tree_type,
        'board': board,
        'min_samples_leaf': min_leaf,
        'tree_stats': {
            'max_depth': int(tree.max_depth),
            'n_leaves': int(tree.n_leaves),
            'n_nodes': int(tree.node_count),
            'n_features': len([f for f in feature_columns if clf.feature_importances_[feature_columns.index(f)] > 0])
        },
        'actions': sorted(actions),
        'feature_importance': feature_importance,
        'nodes': nodes,
        'leaves': leaf_stats
    }

    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Metadata saved: {output_path}")
    print(f"  Features used: {metadata['tree_stats']['n_features']}")
    print(f"  Top 3 features: {list(feature_importance.keys())[:3]}")


def export_feature_importance(clf: DecisionTreeClassifier, feature_columns: List[str],
                              output_path: str):
    """
    Export feature importance to CSV

    Args:
        clf: Trained classifier
        feature_columns: List of feature names
        output_path: Path to save CSV file
    """
    importance_data = []
    for i, feat in enumerate(feature_columns):
        importance = clf.feature_importances_[i]
        if importance > 0:
            importance_data.append({
                'feature': feat,
                'importance': importance
            })

    df = pd.DataFrame(importance_data)
    df = df.sort_values('importance', ascending=False).reset_index(drop=True)
    df['importance'] = df['importance'].round(4)

    df.to_csv(output_path, index=False)
    print(f"Feature importance saved: {output_path}")


def main():
    """Main function to build both matrices"""

    # Board (string)
    board = '9s6d5c'

    print("=" * 60)
    print("Building Bucket Matrices and Decision Trees")
    print("=" * 60)
    print(f"\nBoard: {board}")
    print()

    # Create output folder
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # ===== MATRIX 1: Lead (1/2 POT + CHECK) =====
    print("\n" + "=" * 60)
    print("MATRIX 1: Lead (1/2 POT + CHECK)")
    print("=" * 60)

    range_files_1 = {
        'bet_1/2pot': '/mnt/c/JN/test ranges/9s6d5c/1_2 POT.csv',
        'check': '/mnt/c/JN/test ranges/9s6d5c/CHECK.csv'
    }

    df_combined_1 = combine_ranges(range_files_1, board)
    df_matrix_1, actions_1 = build_bucket_matrix(df_combined_1)

    # Save matrix
    matrix_file_1 = output_dir / 'bucket_matrix_lead_9s6d5c.csv'
    df_matrix_1.to_csv(matrix_file_1, index=False)
    print(f"\nMatrix 1 saved: {matrix_file_1}")

    # Build trees with different min_leaf
    for min_leaf in [1, 10, 50]:
        print(f"\n--- min_leaf = {min_leaf} ---")
        clf_1, features_1 = build_decision_tree(df_matrix_1, actions_1, min_leaf=min_leaf)

        # Export to Mermaid
        mermaid_file_1 = output_dir / f'tree_lead_9s6d5c_min{min_leaf}.mmd'
        export_tree_to_mermaid(clf_1, features_1, actions_1, str(mermaid_file_1))

        # Export metadata
        json_file_1 = output_dir / f'tree_lead_9s6d5c_min{min_leaf}_metadata.json'
        export_tree_metadata(clf_1, features_1, actions_1, board, 'lead', min_leaf, str(json_file_1))

        # Export feature importance
        importance_file_1 = output_dir / f'tree_lead_9s6d5c_min{min_leaf}_importance.csv'
        export_feature_importance(clf_1, features_1, str(importance_file_1))

    # ===== MATRIX 2: NoLead (NoLead_1/2 POT + NoLead_CHECK) =====
    print("\n" + "=" * 60)
    print("MATRIX 2: NoLead (NoLead_1/2 POT + NoLead_CHECK)")
    print("=" * 60)

    range_files_2 = {
        'bet_1/2pot': '/mnt/c/JN/test ranges/9s6d5c/NoLead_1_2 POT.csv',
        'check': '/mnt/c/JN/test ranges/9s6d5c/NoLead_CHECK.csv'
    }

    df_combined_2 = combine_ranges(range_files_2, board)
    df_matrix_2, actions_2 = build_bucket_matrix(df_combined_2)

    # Save matrix
    matrix_file_2 = output_dir / 'bucket_matrix_nolead_9s6d5c.csv'
    df_matrix_2.to_csv(matrix_file_2, index=False)
    print(f"\nMatrix 2 saved: {matrix_file_2}")

    # Build trees with different min_leaf
    for min_leaf in [1, 10, 50]:
        print(f"\n--- min_leaf = {min_leaf} ---")
        clf_2, features_2 = build_decision_tree(df_matrix_2, actions_2, min_leaf=min_leaf)

        # Export to Mermaid
        mermaid_file_2 = output_dir / f'tree_nolead_9s6d5c_min{min_leaf}.mmd'
        export_tree_to_mermaid(clf_2, features_2, actions_2, str(mermaid_file_2))

        # Export metadata
        json_file_2 = output_dir / f'tree_nolead_9s6d5c_min{min_leaf}_metadata.json'
        export_tree_metadata(clf_2, features_2, actions_2, board, 'nolead', min_leaf, str(json_file_2))

        # Export feature importance
        importance_file_2 = output_dir / f'tree_nolead_9s6d5c_min{min_leaf}_importance.csv'
        export_feature_importance(clf_2, features_2, str(importance_file_2))

    # Final statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"\nBoard: {board}")
    print(f"\nMatrix 1 (Lead):")
    print(f"  Buckets: {len(df_matrix_1)}")
    print(f"  Actions: {actions_1}")
    print(f"\nMatrix 2 (NoLead):")
    print(f"  Buckets: {len(df_matrix_2)}")
    print(f"  Actions: {actions_2}")
    print(f"\nAll files saved in: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
