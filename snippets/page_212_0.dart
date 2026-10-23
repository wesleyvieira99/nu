import 'package:flutter/material.dart';

Widget renderProposedNode(
  Map<String, Object?> node,
  void Function(String) dispatch,
) {
  switch (node['type']) {
    case 'text':
      return Text(node['text'] as String);
    case 'action':
      final action = node['action'] as String;
      const allowed = {'view-invoice', 'open-support'};
      if (!allowed.contains(action)) {
        throw const FormatException('Unknown action');
      }
      return Semantics(
        button: true,
        onTap: () => dispatch(action),
        label: node['accessible_name'] as String,
        child: ExcludeSemantics(
          child: ElevatedButton(
            onPressed: () => dispatch(action),
            child: Text(node['text'] as String),
          ),
        ),
      );
    default:
      throw const FormatException('Unknown node type');
  }
}